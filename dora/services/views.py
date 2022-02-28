from django.conf import settings
from django.db.models import Q
from django.http.response import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, pagination, permissions, serializers, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from dora.admin_express.models import City
from dora.core.notify import send_mattermost_notification
from dora.services.emails import send_service_feedback_email
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
    ServiceCategories,
    ServiceKind,
    ServiceModificationHistoryItem,
    ServiceSubCategories,
)
from dora.structures.models import Structure, StructureMember

from .serializers import (
    AnonymousServiceSerializer,
    FeedbackSerializer,
    ServiceListSerializer,
    ServiceSerializer,
)


class FlatPagination(pagination.PageNumberPagination):
    page_size_query_param = "count"

    def get_paginated_response(self, data):
        return Response(data)


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
        if request.method == "DELETE" and not obj.is_suggestion:
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
    pagination_class = FlatPagination

    lookup_field = "slug"

    def get_my_services(self, user):
        if not user or not user.is_authenticated:
            return Service.objects.none()
        return Service.objects.filter(structure__membership__user=user)

    def get_queryset(self):
        qs = None
        user = self.request.user
        only_mine = self.request.query_params.get("mine")
        structure_slug = self.request.query_params.get("structure")
        published_only = self.request.query_params.get("published")

        if only_mine:
            qs = self.get_my_services(user)
        # Everybody can see published services
        elif not user or not user.is_authenticated:
            qs = Service.objects.filter(is_draft=False, is_suggestion=False)
        # Staff can see everything
        elif user.is_staff:
            qs = Service.objects.all()
        else:
            # Authentified users can see everything in their structure
            # plus published services for other structures
            qs = Service.objects.filter(
                Q(is_draft=False, is_suggestion=False)
                | Q(structure__membership__user=user)
            )
        if structure_slug:
            qs = qs.filter(structure__slug=structure_slug)
        if published_only:
            qs = qs.filter(is_draft=False, is_suggestion=False)
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
        last_drafts = Service.objects.filter(
            is_draft=True,
            creator=user,
        ).order_by("-modification_date")
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
        structure = service.structure
        draft = "(brouillon) " if service.is_draft else ""
        send_mattermost_notification(
            f":tada: Nouveau service {draft} “{service.name}” créé dans la structure : **{structure.name} ({structure.department})**\n{settings.FRONTEND_URL}/services/{service.slug}"
        )

    def perform_update(self, serializer):
        if not serializer.instance.is_draft:
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
        serializer.save(last_editor=self.request.user)


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

    def filter_custom_choices(choices):
        user = request.user
        if not user.is_authenticated:
            return choices.filter(structure_id=None)
        if user.is_staff:
            return choices
        user_structures = StructureMember.objects.filter(user=user).values_list(
            "structure_id", flat=True
        )
        return choices.filter(
            Q(structure_id__in=user_structures) | Q(structure_id=None)
        )

    result = {
        "categories": [
            {"value": c[0], "label": c[1]} for c in ServiceCategories.choices
        ],
        "subcategories": [
            {"value": c[0], "label": c[1]} for c in ServiceSubCategories.choices
        ],
        "kinds": [{"value": c[0], "label": c[1]} for c in ServiceKind.choices],
        "access_conditions": AccessConditionSerializer(
            filter_custom_choices(AccessCondition.objects.all()),
            many=True,
            context={"request": request},
        ).data,
        "concerned_public": ConcernedPublicSerializer(
            filter_custom_choices(ConcernedPublic.objects.all()),
            many=True,
            context={"request": request},
        ).data,
        "requirements": RequirementSerializer(
            filter_custom_choices(Requirement.objects.all()),
            many=True,
            context={"request": request},
        ).data,
        "credentials": CredentialSerializer(
            filter_custom_choices(Credential.objects.all()),
            many=True,
            context={"request": request},
        ).data,
        "beneficiaries_access_modes": [
            {"value": c[0], "label": c[1]} for c in BeneficiaryAccessMode.choices
        ],
        "coach_orientation_modes": [
            {"value": c[0], "label": c[1]} for c in CoachOrientationMode.choices
        ],
        "location_kinds": [
            {"value": c[0], "label": c[1]} for c in LocationKind.choices
        ],
        "diffusion_zone_type": [
            {"value": c[0], "label": c[1]} for c in AdminDivisionType.choices
        ],
    }
    return Response(result)


class SearchResultSerializer(ServiceSerializer):
    class Meta:
        model = Service
        fields = [
            "category_display",
            "city",
            "name",
            "postal_code",
            "short_desc",
            "slug",
            "structure_info",
            "structure",
        ]


@api_view()
@permission_classes([permissions.AllowAny])
def search(request):
    category = request.GET.get("cat", "")
    subcategory = request.GET.get("sub", "")
    city_code = request.GET.get("city", "")
    kinds = request.GET.get("kinds", "")
    has_fee_param = request.GET.get("has_fee", "")

    has_fee = None
    if has_fee_param in ("1", 1, "True", "true", "t", "T"):
        has_fee = True
    elif has_fee_param in ("0", 0, "False", "false", "f", "F"):
        has_fee = False

    services = Service.objects.filter(
        category=category, is_draft=False, is_suggestion=False
    )
    if has_fee is True:
        services = services.filter(has_fee=True)
    elif has_fee is False:
        services = services.filter(has_fee=False)
    if kinds:
        services = services.filter(kinds__overlap=kinds.split(","))

    if subcategory:
        services = services.filter(subcategories__contains=[subcategory])

    city = get_object_or_404(City, pk=city_code)

    geofiltered_services = services.filter(
        Q(diffusion_zone_type=AdminDivisionType.COUNTRY)
        | (
            Q(diffusion_zone_type=AdminDivisionType.CITY)
            & Q(diffusion_zone_details=city.code)
        )
        | (
            Q(diffusion_zone_type=AdminDivisionType.EPCI)
            & Q(diffusion_zone_details__in=city.epci.split("/"))
        )
        | (
            Q(diffusion_zone_type=AdminDivisionType.DEPARTMENT)
            & Q(diffusion_zone_details=city.department)
        )
        | (
            Q(diffusion_zone_type=AdminDivisionType.REGION)
            & Q(diffusion_zone_details=city.region)
        )
    )

    # Exclude suspended services
    results = geofiltered_services.filter(
        Q(suspension_date=None) | Q(suspension_date__gte=timezone.now())
    )

    return Response(
        SearchResultSerializer(results, many=True, context={"request": request}).data
    )
