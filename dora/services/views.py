import humanize
from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django.db.models import Case, IntegerField, Q, Value, When
from django.http.response import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, permissions, serializers, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from dora.admin_express.models import City
from dora.admin_express.utils import arrdt_to_main_insee_code
from dora.core.notify import send_mattermost_notification
from dora.core.pagination import OptionalPageNumberPagination
from dora.core.utils import FALSY_VALUES, TRUTHY_VALUES
from dora.services.emails import send_service_feedback_email
from dora.services.enums import ServiceStatus
from dora.services.models import (
    AccessCondition,
    AdminDivisionType,
    BeneficiaryAccessMode,
    CoachOrientationMode,
    ConcernedPublic,
    Credential,
    LocationKind,
    Requirement,
    Service,
    ServiceCategory,
    ServiceKind,
    ServiceModel,
    ServiceModificationHistoryItem,
    ServiceSubCategory,
)
from dora.services.utils import filter_services_by_city_code
from dora.structures.models import Structure, StructureMember

from .serializers import (
    AnonymousServiceSerializer,
    FeedbackSerializer,
    ServiceListSerializer,
    ServiceModelSerializer,
    ServiceSerializer,
)


class ServicePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if request.method == "DELETE":
            return user and user.is_authenticated

        # Only authentified users can get the last draft
        if view.action == "get_last_draft":
            return user and user.is_authenticated

        # Anybody can read
        if request.method in permissions.SAFE_METHODS:
            return True

        # Authentified user can read and write
        return user and user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user
        # Only suggestions can be deleted
        if request.method == "DELETE" and not obj.status == ServiceStatus.SUGGESTION:
            return False

        # Anybody can read
        if request.method in permissions.SAFE_METHODS:
            return True

        # Staff can do anything
        if user.is_staff:
            return True

        # People can only edit their Structures' stuff
        user_structures = Structure.objects.filter(membership__user=user)
        return obj.structure in user_structures


class ServiceViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [ServicePermission]
    pagination_class = OptionalPageNumberPagination

    lookup_field = "slug"

    def get_queryset(self):
        qs = None
        user = self.request.user
        only_mine = self.request.query_params.get("mine") in TRUTHY_VALUES
        only_archived = self.request.query_params.get("archived") in TRUTHY_VALUES
        structure_slug = self.request.query_params.get("structure")
        if only_archived and not structure_slug:
            raise serializers.ValidationError("Il faut préciser la structure")
        published_only = self.request.query_params.get("published")

        all_services = (
            Service.objects.all()
            .select_related(
                "structure",
            )
            .prefetch_related(
                "kinds",
                "categories",
                "subcategories",
                "access_conditions",
                "concerned_public",
                "beneficiaries_access_modes",
                "coach_orientation_modes",
                "requirements",
                "credentials",
                "location_kinds",
            )
        )
        qs = None
        if only_mine:
            if not user or not user.is_authenticated:
                qs = Service.objects.none()
            else:
                qs = all_services.filter(structure__membership__user=user)
        elif only_archived:
            if not user or not user.is_authenticated:
                qs = Service.objects.none()
            else:
                if user.is_staff:
                    qs = all_services.filter(status=ServiceStatus.ARCHIVED)
                else:
                    qs = all_services.filter(
                        structure__membership__user=user, status=ServiceStatus.ARCHIVED
                    )
        # Everybody can see published services
        elif not user or not user.is_authenticated:
            qs = all_services.filter(status=ServiceStatus.PUBLISHED)
        # Staff can see everything
        elif user.is_staff:
            qs = all_services
        else:
            # Authentified users can see everything in their structure
            # plus published services for other structures
            qs = all_services.filter(
                Q(status=ServiceStatus.PUBLISHED) | Q(structure__membership__user=user)
            )
        if structure_slug:
            qs = qs.filter(structure__slug=structure_slug)

        if published_only:
            qs = qs.filter(status=ServiceStatus.PUBLISHED)

        return qs.order_by("-modification_date").distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return ServiceListSerializer
        # We only want to expose the full ServiceSerializer if the user was
        # effectively validated:
        # - either they are staff
        # - either they have a validated email, and are members of a structure
        user = self.request.user
        if user.is_authenticated and (
            user.is_staff
            or (user.is_valid and StructureMember.objects.filter(user=user).exists())
        ):
            return ServiceSerializer
        return AnonymousServiceSerializer

    @action(detail=False, methods=["get"], url_path="last-draft")
    def get_last_draft(self, request):
        user = request.user
        last_drafts = (
            Service.objects.draft()
            .filter(
                creator=user,
            )
            .order_by("-modification_date")
        )
        if not user.is_staff:
            last_drafts = last_drafts.filter(
                structure__membership__user__id=user.id,
            )
        last_draft = last_drafts.first()
        if last_draft:
            return Response(
                ServiceSerializer(last_draft, context={"request": request}).data
            )
        raise Http404

    @action(
        detail=True,
        methods=["post"],
        url_path="feedback",
        permission_classes=[permissions.AllowAny],
    )
    def post_feedback(self, request, slug):
        service = self.get_object()
        serializer = FeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        send_service_feedback_email(service, d["full_name"], d["email"], d["message"])
        return Response(status=201)

    def perform_create(self, serializer):
        service = serializer.save(
            creator=self.request.user, last_editor=self.request.user
        )
        if service.status == ServiceStatus.DRAFT:
            self._send_draft_service_created_notification(service)
        elif service.status == ServiceStatus.PUBLISHED:
            self._send_service_published_notification(service)
        if service.model:
            service.last_sync_checksum = service.model.sync_checksum
        # Force a save to update the sync_checksum
        service.save()

    def _send_draft_service_created_notification(self, service):
        structure = service.structure
        user = self.request.user
        send_mattermost_notification(
            f":tada: Nouveau brouillon “{service.name}” créé dans la structure : **{structure.name} ({structure.department})** par {user.get_full_name()}\n{settings.FRONTEND_URL}/services/{service.slug}"
        )

    def _send_service_published_notification(self, service):
        structure = service.structure
        time_elapsed = (
            service.publication_date - service.creation_date
            if service.publication_date > service.creation_date
            else 0
        )
        humanize.i18n.activate("fr_FR")
        time_elapsed_h = humanize.naturaldelta(time_elapsed, months=True)
        user = self.request.user
        send_mattermost_notification(
            f":100: Service “{service.name}” publié dans la structure : **{structure.name} ({structure.department})** par {user.get_full_name()}, {time_elapsed_h} après sa création\n{settings.FRONTEND_URL}/services/{service.slug}"
        )

    def _log_history(self, serializer):
        changed_fields = []
        for key, value in serializer.validated_data.items():
            original_value = getattr(serializer.instance, key)
            if type(original_value).__name__ == "ManyRelatedManager":
                original_value = set(original_value.all())
                has_changed = set(value) != original_value
            else:
                has_changed = value != original_value
            if has_changed:
                changed_fields.append(key)
        if changed_fields:
            ServiceModificationHistoryItem.objects.create(
                service=serializer.instance,
                user=self.request.user,
                fields=changed_fields,
            )

    def perform_update(self, serializer):
        mark_synced = self.request.data.get("mark_synced", "") in TRUTHY_VALUES
        was_draft = serializer.instance.status == ServiceStatus.DRAFT
        if not was_draft:
            self._log_history(serializer)
        service = serializer.save(last_editor=self.request.user)
        if (
            was_draft
            and service.status == ServiceStatus.PUBLISHED
            and not service.history_item.all().exists()
        ):
            self._send_service_published_notification(service)

        if mark_synced and service.model:
            service.last_sync_checksum = service.model.sync_checksum
        # Force a save to update the sync_checksum
        service.save()


class ModelViewSet(ServiceViewSet):
    def get_serializer_class(self):
        return ServiceModelSerializer

    def get_queryset(self):
        qs = None
        user = self.request.user
        only_mine = self.request.query_params.get("mine")

        structure_slug = self.request.query_params.get("structure")

        all_models = (
            ServiceModel.objects.all()
            .select_related(
                "structure",
            )
            .prefetch_related(
                "kinds",
                "categories",
                "subcategories",
                "access_conditions",
                "concerned_public",
                "beneficiaries_access_modes",
                "coach_orientation_modes",
                "requirements",
                "credentials",
                "location_kinds",
            )
        )
        qs = None
        if only_mine:
            if not user or not user.is_authenticated:
                qs = ServiceModel.objects.none()
            else:
                qs = all_models.filter(structure__membership__user=user)
        # Everybody can see models
        else:
            qs = all_models

        if structure_slug:
            qs = qs.filter(structure__slug=structure_slug)

        return qs.order_by("-modification_date").distinct()

    def perform_create(self, serializer):
        user = self.request.user
        user_structures = Structure.objects.filter(membership__user=user)
        service_slug = self.request.data.get("service")
        service = None
        if service_slug:
            try:
                service = Service.objects.get(slug=service_slug)
            except Service.DoesNotExist:
                raise Http404

            if service.model:
                raise serializers.ValidationError(
                    "Impossible de copier un service synchronisé"
                )

            # On peut uniquement transformer un service d'une de nos structures
            if not user.is_staff and service.structure not in user_structures:
                raise PermissionDenied

        structure_slug = self.request.data.get("structure")
        try:
            structure = Structure.objects.get(slug=structure_slug)
        except Structure.DoesNotExist:
            raise Http404
        # On peut uniquement copier vers une structure dont on fait partie
        user_structures = Structure.objects.filter(membership__user=user)
        if not (user.is_staff or structure in user_structures):
            raise PermissionDenied

        # # On peut uniquement copier un service d'une de nos structures
        # if service.structure not in user_structures:
        #     raise PermissionDenied

        model = serializer.save(
            creator=self.request.user,
            last_editor=self.request.user,
            is_model=True,
        )
        structure = model.structure

        send_mattermost_notification(
            f":clipboard: Nouveau modèle “{model.name}” créé dans la structure : **{structure.name} ({structure.department})**\n{settings.FRONTEND_URL}/modeles/{model.slug}"
        )
        # TODO "à partir du service………"
        # Force a save to update the sync_checksum
        model.save()
        if service:
            service.model = model
            service.last_sync_checksum = model.sync_checksum
            service.save()


@api_view()
@permission_classes([permissions.AllowAny])
def options(request):
    class CustomChoiceSerializer(serializers.ModelSerializer):
        value = serializers.IntegerField(source="id")
        label = serializers.CharField(source="name")
        structure = serializers.SlugRelatedField(slug_field="slug", read_only=True)

        class Meta:
            fields = ["value", "label", "structure"]

    class AccessConditionSerializer(CustomChoiceSerializer):
        class Meta(CustomChoiceSerializer.Meta):
            model = AccessCondition

    class ConcernedPublicSerializer(CustomChoiceSerializer):
        class Meta(CustomChoiceSerializer.Meta):
            model = ConcernedPublic

    class RequirementSerializer(CustomChoiceSerializer):
        class Meta(CustomChoiceSerializer.Meta):
            model = Requirement

    class CredentialSerializer(CustomChoiceSerializer):
        class Meta(CustomChoiceSerializer.Meta):
            model = Credential

    class ServiceCategorySerializer(serializers.ModelSerializer):
        class Meta:
            model = ServiceCategory
            fields = ["value", "label"]

    class ServiceSubCategorySerializer(serializers.ModelSerializer):
        class Meta:
            model = ServiceSubCategory
            fields = ["value", "label"]

    class ServiceKindSerializer(serializers.ModelSerializer):
        class Meta:
            model = ServiceKind
            fields = ["value", "label"]

    class BeneficiaryAccessModeSerializer(serializers.ModelSerializer):
        class Meta:
            model = BeneficiaryAccessMode
            fields = ["value", "label"]

    class CoachOrientationModeSerializer(serializers.ModelSerializer):
        class Meta:
            model = CoachOrientationMode
            fields = ["value", "label"]

    class LocationKindSerializer(serializers.ModelSerializer):
        class Meta:
            model = LocationKind
            fields = ["value", "label"]

    def filter_custom_choices(choices):
        user = request.user
        if not user.is_authenticated:
            return choices.filter(structure_id=None)
        if user.is_staff or user.is_bizdev:
            return choices
        user_structures = StructureMember.objects.filter(user=user).values_list(
            "structure_id", flat=True
        )
        return choices.filter(
            Q(structure_id__in=user_structures) | Q(structure_id=None)
        )

    result = {
        "categories": ServiceCategorySerializer(
            ServiceCategory.objects.all(), many=True
        ).data,
        "subcategories": ServiceSubCategorySerializer(
            ServiceSubCategory.objects.all(), many=True
        ).data,
        "kinds": ServiceKindSerializer(ServiceKind.objects.all(), many=True).data,
        "beneficiaries_access_modes": BeneficiaryAccessModeSerializer(
            BeneficiaryAccessMode.objects.all(), many=True
        ).data,
        "coach_orientation_modes": CoachOrientationModeSerializer(
            CoachOrientationMode.objects.all(), many=True
        ).data,
        "location_kinds": LocationKindSerializer(
            LocationKind.objects.all(), many=True
        ).data,
        "access_conditions": AccessConditionSerializer(
            filter_custom_choices(
                AccessCondition.objects.select_related("structure").all()
            ),
            many=True,
            context={"request": request},
        ).data,
        "concerned_public": ConcernedPublicSerializer(
            filter_custom_choices(
                ConcernedPublic.objects.select_related("structure").all()
            ),
            many=True,
            context={"request": request},
        ).data,
        "requirements": RequirementSerializer(
            filter_custom_choices(
                Requirement.objects.select_related("structure").all()
            ),
            many=True,
            context={"request": request},
        ).data,
        "credentials": CredentialSerializer(
            filter_custom_choices(Credential.objects.select_related("structure").all()),
            many=True,
            context={"request": request},
        ).data,
        "diffusion_zone_type": [
            {"value": c[0], "label": c[1]} for c in AdminDivisionType.choices
        ],
    }
    return Response(result)


class SearchResultSerializer(ServiceListSerializer):
    distance = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            "categories_display",
            "name",
            "short_desc",
            "slug",
            "structure_info",
            "structure",
            "distance",
            "location",
        ]

    def get_distance(self, obj):
        return int(obj.distance.km) if obj.distance is not None else None

    def get_location(self, obj):
        if obj.location_kinds.filter(value="en-presentiel").exists():
            return f"{obj.postal_code}, {obj.city}"
        elif obj.location_kinds.filter(value="a-distance").exists():
            return "À distance"
        else:
            return ""


def _sort_search_results(services, location):
    services = services.order_by().annotate(
        diffusion_sort=Case(
            When(diffusion_zone_type=AdminDivisionType.CITY, then=1),
            When(diffusion_zone_type=AdminDivisionType.EPCI, then=2),
            When(diffusion_zone_type=AdminDivisionType.DEPARTMENT, then=3),
            When(diffusion_zone_type=AdminDivisionType.REGION, then=4),
            default=5,
        )
    )
    # 1) services ayant un lieu de déroulement, à moins de 100km
    services_on_site = (
        services.filter(location_kinds__value="en-presentiel")
        .annotate(distance=Distance("geom", location))
        .filter(distance__lte=D(km=100))
        .order_by("distance", "diffusion_sort", "-modification_date")
    )
    # 2) services sans lieu de déroulement
    services_remote = (
        services.exclude(location_kinds__value="en-presentiel")
        .annotate(distance=Value(None, output_field=IntegerField()))
        .order_by("diffusion_sort", "-modification_date")
    )

    return list(services_on_site) + list(services_remote)


@api_view()
@permission_classes([permissions.AllowAny])
def search(request):
    category = request.GET.get("cat", "")
    subcategory = request.GET.get("sub", "")
    city_code = request.GET.get("city", "")
    kinds = request.GET.get("kinds", "")
    has_fee_param = request.GET.get("has_fee", "")

    has_fee = None
    if has_fee_param in TRUTHY_VALUES:
        has_fee = True
    elif has_fee_param in FALSY_VALUES:
        has_fee = False

    services = (
        Service.objects.published()
        .select_related(
            "structure",
        )
        .prefetch_related(
            "kinds",
            "categories",
            "subcategories",
        )
    )
    if category:
        services = services.filter(categories__value=category)
    if has_fee is True:
        services = services.filter(has_fee=True)
    elif has_fee is False:
        services = services.filter(has_fee=False)
    if kinds:
        services = services.filter(kinds__value__in=kinds.split(","))

    if subcategory:
        services = services.filter(subcategories__value=subcategory)

    geofiltered_services = filter_services_by_city_code(services, city_code)

    city_code = arrdt_to_main_insee_code(city_code)
    city = get_object_or_404(City, pk=city_code)

    # Exclude suspended services
    results = _sort_search_results(
        geofiltered_services.filter(
            Q(suspension_date=None) | Q(suspension_date__gte=timezone.now())
        ).distinct(),
        city.geom,
    )

    serializer = SearchResultSerializer(
        results, many=True, context={"request": request}
    )
    return Response(serializer.data)
