import requests
from django.db.models import Q
from django.http.response import Http404
from django.utils import timezone
from rest_framework import (
    exceptions,
    mixins,
    permissions,
    serializers,
    status,
    viewsets,
)
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from dora import data_inclusion
from dora.core.models import ModerationStatus
from dora.core.notify import send_moderation_notification
from dora.core.pagination import OptionalPageNumberPagination
from dora.core.utils import TRUTHY_VALUES
from dora.services.emails import send_service_feedback_email
from dora.services.enums import ServiceStatus
from dora.services.models import (
    AccessCondition,
    AdminDivisionType,
    BeneficiaryAccessMode,
    Bookmark,
    CoachOrientationMode,
    ConcernedPublic,
    Credential,
    LocationKind,
    Requirement,
    SavedSearch,
    Service,
    ServiceCategory,
    ServiceFee,
    ServiceKind,
    ServiceModel,
    ServiceModificationHistoryItem,
    ServiceStatusHistoryItem,
    ServiceSubCategory,
)
from dora.services.utils import synchronize_service_from_model
from dora.stats.models import DeploymentLevel, DeploymentState
from dora.structures.models import Structure, StructureMember

from .serializers import (
    AnonymousServiceSerializer,
    BookmarkSerializer,
    FeedbackSerializer,
    SavedSearchSerializer,
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


def get_visible_services(user):
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
    return qs.distinct()


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
        user = self.request.user
        structure_slug = self.request.query_params.get("structure")
        published_only = self.request.query_params.get("published") in TRUTHY_VALUES

        qs = get_visible_services(user)

        if structure_slug:
            qs = qs.filter(structure__slug=structure_slug)

        if published_only:
            qs = qs.filter(status=ServiceStatus.PUBLISHED)

        return qs.order_by("-modification_date")

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

        if service.status == ServiceStatus.PUBLISHED:
            send_moderation_notification(
                service,
                self.request.user,
                "Service publié",
                ModerationStatus.NEED_INITIAL_MODERATION,
            )
        if service.model:
            service.last_sync_checksum = service.model.sync_checksum
            service.save()

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
            send_moderation_notification(
                service,
                self.request.user,
                "Service publié",
                ModerationStatus.NEED_INITIAL_MODERATION,
            )
        elif changed_fields and service.status == ServiceStatus.PUBLISHED:
            send_moderation_notification(
                service,
                self.request.user,
                f"Service modifié ({' / '.join(changed_fields)})",
                ModerationStatus.NEED_NEW_MODERATION,
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


class BookmarkViewSet(
    viewsets.GenericViewSet,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BookmarkSerializer

    def get_queryset(self):
        user = self.request.user
        visible_and_active_services = get_visible_services(user).exclude(
            status=ServiceStatus.ARCHIVED
        )
        return Bookmark.objects.filter(
            Q(service__isnull=True) | Q(service__in=visible_and_active_services),
            user=user,
        ).order_by("-creation_date")

    def create(self, request):
        slug = request.data.get("slug")
        is_di = request.data.get("is_di")
        service = None
        if slug and not is_di:
            try:
                service = Service.objects.get(slug=slug)
            except Service.DoesNotExist:
                raise NotFound
        if service and not service.can_read(request.user):
            raise PermissionDenied

        bookmark, created = Bookmark.objects.get_or_create(
            user=self.request.user,
            service=service if not is_di else None,
            di_id=slug if is_di else "",
        )
        if not created:
            raise serializers.ValidationError("ce bookmark existe déjà")

        return Response(status=status.HTTP_201_CREATED)


class SavedSearchViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = SavedSearchSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return SavedSearch.objects.filter(user=user).order_by("-creation_date")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(
        detail=True,
        methods=["get"],
        url_path="recent",
        permission_classes=[permissions.AllowAny],
    )
    def get_recent_services(self, request, _slug):
        saved_search = self.get_object()
        if saved_search.user != request.user:
            raise exceptions.PermissionDenied()

        # serializer = FeedbackSerializer(data=request.data)
        # serializer.is_valid(raise_exception=True)
        # d = serializer.validated_data
        # send_service_feedback_email(service, d["full_name"], d["email"], d["message"])
        # return Response(status=201)


class ModelViewSet(ServiceViewSet):
    def get_serializer_class(self):
        return ServiceModelSerializer

    def get_queryset(self):
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

                    # On ne vérifie pas les droits sur les services liés au modèle,
                    # en partant du principe que s'il peut modifier le modèle
                    # alors il peut modifier les services liés
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


@api_view()
@permission_classes([permissions.AllowAny])
def service_di(
    request,
    di_id: str,
    di_client: data_inclusion.DataInclusionClient,
):
    """Retrieve a single service from data.inclusion.

    The ``di_client`` acts as an entrypoint to the data.inclusion service repository.

    The output format matches the ServiceSerializer.
    """

    source_di, di_service_id = di_id.split("--")

    try:
        raw_service = di_client.retrieve_service(source=source_di, id=di_service_id)
    except requests.ConnectionError:
        return Response(status=status.HTTP_502_BAD_GATEWAY)

    if raw_service is None:
        return Response(status=status.HTTP_404_NOT_FOUND)

    return Response(data_inclusion.map_service(raw_service))


@api_view()
@permission_classes([permissions.AllowAny])
def search(request, di_client=None):
    city_code = request.GET.get("city")
    categories = request.GET.get("cats")
    subcategories = request.GET.get("subs")
    kinds = request.GET.get("kinds")
    fees = request.GET.get("fees")

    categories_list = categories.split(",") if categories is not None else None
    subcategories_list = subcategories.split(",") if subcategories is not None else None
    kinds_list = kinds.split(",") if kinds is not None else None
    fees_list = fees.split(",") if fees is not None else None
    from .search import search_services

    sorted_results = search_services(
        request=request,
        di_client=di_client,
        city_code=city_code,
        categories=categories_list,
        subcategories=subcategories_list,
        kinds=kinds_list,
        fees=fees_list,
    )

    return Response(sorted_results)
