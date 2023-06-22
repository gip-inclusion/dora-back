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
from dora.core.models import ModerationStatus
from dora.core.notify import send_mattermost_notification, send_moderation_notification
from dora.core.pagination import OptionalPageNumberPagination
from dora.core.utils import TRUTHY_VALUES
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
    ServiceFee,
    ServiceKind,
    ServiceModel,
    ServiceModificationHistoryItem,
    ServiceStatusHistoryItem,
    ServiceSubCategory,
)
from dora.services.utils import (
    filter_services_by_city_code,
    synchronize_service_from_model,
)
from dora.stats.models import DeploymentLevel, DeploymentState
from dora.structures.models import Structure, StructureMember

from .models import Bookmark
from .serializers import (
    AnonymousServiceSerializer,
    FeedbackSerializer,
    ServiceListSerializer,
    ServiceModelSerializer,
    ServiceSerializer,
)
from .utils import update_sync_checksum


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

    def has_object_permission(self, request, view, service):
        user = request.user
        # Only suggestions can be deleted
        if (
            request.method == "DELETE"
            and not service.status == ServiceStatus.SUGGESTION
        ):
            return False

        # Anybody can read
        if request.method in permissions.SAFE_METHODS:
            return True

        return service.can_write(user)


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
        structure_slug = self.request.query_params.get("structure")
        published_only = self.request.query_params.get("published") in TRUTHY_VALUES

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

        # Everybody can see published services
        if not user or not user.is_authenticated:
            qs = all_services.filter(status=ServiceStatus.PUBLISHED)
        # Staff can see everything
        elif user.is_staff:
            qs = all_services
        elif user.is_manager and user.department:
            qs = all_services.filter(
                Q(status=ServiceStatus.PUBLISHED)
                | Q(structure__department=user.department)
                | Q(structure__membership__user=user)
            )
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

    @action(
        detail=True,
        methods=["post"],
        url_path="set-bookmark",
        permission_classes=[permissions.IsAuthenticated],
    )
    def set_bookmark(self, request, slug):
        user = self.request.user
        service = self.get_object()
        wanted_state = self.request.data.get("state")
        if wanted_state:
            Bookmark.objects.get_or_create(service=service, user=user)
        else:
            try:
                bookmark = Bookmark.objects.get(service=service, user=user)
                bookmark.delete()
            except Bookmark.DoesNotExist:
                pass
        return Response(status=204)

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
        pub_date = None
        if serializer.validated_data.get("status") == ServiceStatus.PUBLISHED:
            pub_date = timezone.now()

        service = serializer.save(
            creator=self.request.user,
            last_editor=self.request.user,
            publication_date=pub_date,
            modification_date=timezone.now(),
        )

        if service.status == ServiceStatus.DRAFT:
            self._send_draft_service_created_notification(service)
        elif service.status == ServiceStatus.PUBLISHED:
            self._send_service_published_notification(service, self.request.user)
        if service.model:
            service.last_sync_checksum = service.model.sync_checksum
            service.save()

    def _send_draft_service_created_notification(self, service):
        structure = service.structure
        user = self.request.user
        send_mattermost_notification(
            f":tada: Nouveau brouillon “{service.name}” créé dans la structure : **{structure.name} ({structure.department})** par {user.get_full_name()}\n{settings.FRONTEND_URL}/services/{service.slug}"
        )

    def _send_service_published_notification(self, service, user):
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
            f":100: Service “{service.name}” publié dans la structure : **{structure.name} ({structure.department})** par {user.get_full_name()}, {time_elapsed_h} après sa création\n{service.get_absolute_url()}"
        )
        send_moderation_notification(
            service,
            user,
            "Service publié",
            ModerationStatus.NEED_INITIAL_MODERATION,
        )

    def _send_service_modified_notification(self, service, user, changed_fields):
        send_moderation_notification(
            service,
            user,
            f"Service modifié ({' / '.join(changed_fields)})",
            ModerationStatus.NEED_NEW_MODERATION,
        )

    def _log_history(self, serializer, new_status=""):
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
                status=new_status,
            )
        return changed_fields

    def _update_status(self, service, new_status, previous_status, user):
        if new_status == ServiceStatus.PUBLISHED:
            service.publication_date = timezone.now()
            service.save()

        ServiceStatusHistoryItem.objects.create(
            service=service,
            user=user,
            new_status=new_status,
            previous_status=previous_status,
        )

    def perform_update(self, serializer):
        mark_synced = self.request.data.get("mark_synced", "") in TRUTHY_VALUES

        status_before_update = serializer.instance.status
        status_after_update = (
            serializer.validated_data.get("status") or status_before_update
        )

        # Historique de modifications
        changed_fields = self._log_history(serializer, status_after_update)

        # Synchronisation avec les modèles
        last_sync_checksum = serializer.instance.last_sync_checksum
        if mark_synced and serializer.instance.model:
            last_sync_checksum = serializer.instance.model.sync_checksum

        # Enregistrement des mises à jour
        service = serializer.save(
            last_editor=self.request.user,
            last_sync_checksum=last_sync_checksum,
            modification_date=timezone.now(),
        )

        # Historique des statuts
        if status_before_update != service.status:
            self._update_status(
                service, service.status, status_before_update, self.request.user
            )

        # Notifications
        newly_published = (
            status_before_update != service.status
            and service.status == ServiceStatus.PUBLISHED
        )
        if newly_published:
            self._send_service_published_notification(service, self.request.user)
        elif changed_fields and service.status == ServiceStatus.PUBLISHED:
            self._send_service_modified_notification(
                service, self.request.user, changed_fields
            )

    @action(
        detail=False,
        methods=["POST"],
        url_path="update-from-model",
        permission_classes=[permissions.IsAuthenticated],
    )
    def update_services_from_model(self, request):
        service_slugs = self.request.data.get("services")

        user = self.request.user
        services = Service.objects.filter(slug__in=service_slugs)

        # Vérification des permissions
        for service in services:
            if not service.can_write(user):
                raise PermissionDenied

        for service in services:
            synchronize_service_from_model(service, service.model)

            service.last_editor = self.request.user
            service.last_sync_checksum = service.model.sync_checksum
            service.modification_date = timezone.now()
            service.save()

        return Response(status=204)

    @action(
        detail=False,
        methods=["POST"],
        url_path="reject-update-from-model",
        permission_classes=[permissions.IsAuthenticated],
    )
    def reject_update_services_from_model(self, request):
        data = self.request.data.get("data")
        user = self.request.user

        for row in data:
            model_slug = row.get("model_slug", None)
            service_slug = row.get("service_slug", None)

            if model_slug and service_slug:
                service = Service.objects.filter(slug=service_slug).first()
                model = ServiceModel.objects.filter(slug=model_slug).first()

                if model and service and service.can_write(user):
                    service.last_sync_checksum = model.sync_checksum
                    service.save()

        return Response(status=204)


class ModelViewSet(ServiceViewSet):
    def get_serializer_class(self):
        return ServiceModelSerializer

    def get_queryset(self):
        qs = None

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

        # Everybody can see models

        qs = all_models
        if structure_slug:
            qs = qs.filter(structure__slug=structure_slug)

        return qs.order_by("-modification_date").distinct()

    def perform_create(self, serializer):
        user = self.request.user
        service_slug = self.request.data.get("service")
        service = None
        # Création d'un modèle à partir d'un service
        if service_slug:
            try:
                service = Service.objects.get(slug=service_slug)
            except Service.DoesNotExist:
                raise Http404

            # On peut uniquement transformer en modèle un service
            # d'une de nos structures
            if not service.structure.can_edit_services(user):
                raise PermissionDenied

            if service.model:
                raise serializers.ValidationError(
                    "Impossible de copier un service synchronisé"
                )

        structure_slug = self.request.data.get("structure")
        try:
            structure = Structure.objects.get(slug=structure_slug)
        except Structure.DoesNotExist:
            raise Http404
        # On peut uniquement copier vers une structure dont on fait partie
        if not structure.can_edit_services(user):
            raise PermissionDenied

        model = serializer.save(
            creator=self.request.user,
            last_editor=self.request.user,
            is_model=True,
            modification_date=timezone.now(),
        )
        assert model.structure == structure
        send_mattermost_notification(
            f":clipboard: Nouveau modèle “{model.name}” créé dans la structure : **{structure.name} ({structure.department})**\n{settings.FRONTEND_URL}/modeles/{model.slug}"
        )
        # TODO "à partir du service………"

        # Doit être fait après la première sauvegarde pour prendre en compte
        # les champs M2M
        model.sync_checksum = update_sync_checksum(model)
        model.save()
        if service:
            service.model = model
            service.last_sync_checksum = model.sync_checksum
            service.save()

    def perform_update(self, serializer):
        changed_fields = self._log_history(serializer)
        model = serializer.save(
            last_editor=self.request.user,
            modification_date=timezone.now(),
        )

        model.sync_checksum = update_sync_checksum(model)
        model.save()

        if changed_fields:
            model.log_note(
                self.request.user,
                f"Modèle modifié ({' / '.join(changed_fields)})",
            )

            if self.request.data.get("update_all_services", "") in TRUTHY_VALUES:
                services = Service.objects.filter(model_id=model.id)

                for service in services:
                    if not service.can_write(self.request.user):
                        continue

                    synchronize_service_from_model(service, model)

                    service.log_note(
                        self.request.user,
                        f"Service modifié automatiquement suite à la mise à jour de son modèle ({' / '.join(changed_fields)})",
                    )

                    ServiceModificationHistoryItem.objects.create(
                        service=service,
                        user=self.request.user,
                        fields=changed_fields,
                        status=service.status,
                    )

                    service.last_editor = self.request.user
                    service.last_sync_checksum = model.sync_checksum
                    service.modification_date = timezone.now()

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

    class ServiceFeeSerializer(serializers.ModelSerializer):
        class Meta:
            model = ServiceFee
            fields = ["value", "label"]

    def filter_custom_choices(choices):
        user = request.user
        if user.is_staff:
            return choices

        filters = Q(structure_id=None)

        if user.is_authenticated:
            user_structures = StructureMember.objects.filter(user=user).values_list(
                "structure_id", flat=True
            )
            filters |= Q(structure_id__in=user_structures)

            if user.is_manager and user.department:
                manager_structures = Structure.objects.filter(
                    department=user.department
                )
                filters |= Q(structure__in=manager_structures)

        return choices.filter(filters)

    result = {
        "categories": ServiceCategorySerializer(
            ServiceCategory.objects.all(), many=True
        ).data,
        "subcategories": ServiceSubCategorySerializer(
            ServiceSubCategory.objects.all(), many=True
        ).data,
        "kinds": ServiceKindSerializer(
            ServiceKind.objects.all().order_by("label"), many=True
        ).data,
        "fee_conditions": ServiceFeeSerializer(
            ServiceFee.objects.all(), many=True
        ).data,
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
        "deployment_departments": [
            s["department_code"]
            for s in DeploymentState.objects.filter(
                state__in=[DeploymentLevel.IN_PROGRESS, DeploymentLevel.FINALIZING]
            ).values()
        ],
    }
    return Response(result)


class SearchResultSerializer(ServiceListSerializer):
    distance = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            "name",
            "short_desc",
            "slug",
            "structure",
            "structure_info",
            "modification_date",
            "diffusion_zone_type",
            "distance",
            "status",
            "location",
        ]

    def get_distance(self, obj):
        return int(obj.distance.km) if obj.distance is not None else None

    def get_location(self, obj):
        if obj.location_kinds.filter(value="en-presentiel").exists():
            return f"{obj.postal_code} {obj.city}"
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
    categories = request.GET.get("cats", "")
    subcategories = request.GET.get("subs", "")
    city_code = request.GET.get("city", "")
    kinds = request.GET.get("kinds", "")
    fees = request.GET.get("fees", "")

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

    if kinds:
        services = services.filter(kinds__value__in=kinds.split(","))

    if fees:
        services = services.filter(fee_condition__value__in=fees.split(","))

    categories_filter = Q()
    if categories:
        categories_filter = Q(categories__value__in=categories.split(","))

    subcategories_filter = Q()
    if subcategories:
        for subcategory in subcategories.split(","):
            cat, subcat = subcategory.split("--")
            if subcat == "autre":
                # Quand on cherche une sous-catégorie de type 'Autre', on veut
                # aussi remonter les services sans sous-catégorie
                all_sister_subcats = ServiceSubCategory.objects.filter(
                    value__startswith=f"{cat}--"
                )
                subcategories_filter |= Q(subcategories__value=subcategory) | (
                    Q(categories__value=cat) & ~Q(subcategories__in=all_sister_subcats)
                )
            else:
                subcategories_filter |= Q(subcategories__value=subcategory)

    services = services.filter(categories_filter | subcategories_filter).distinct()

    geofiltered_services = filter_services_by_city_code(services, city_code)

    city_code = arrdt_to_main_insee_code(city_code)
    city = get_object_or_404(City, pk=city_code)

    # Exclude suspended services
    services_to_display = geofiltered_services.filter(
        Q(suspension_date=None) | Q(suspension_date__gte=timezone.now())
    ).distinct()

    results = _sort_search_results(
        # Display first the services modified after the cutoff date
        services_to_display,
        city.geom,
    )

    serializer = SearchResultSerializer(
        results, many=True, context={"request": request}
    )
    return Response(serializer.data)
