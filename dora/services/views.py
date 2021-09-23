from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django.db.models import Q
from django.http.response import Http404
from django.shortcuts import get_object_or_404
from rest_framework import mixins, permissions, serializers, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from dora.admin_express.models import City
from dora.services.models import (
    AccessCondition,
    BeneficiaryAccessMode,
    CoachOrientationMode,
    ConcernedPublic,
    Credential,
    LocationKind,
    RecurrenceKind,
    Requirement,
    Service,
    ServiceCategories,
    ServiceKind,
    ServiceSubCategories,
)
from dora.structures.models import Structure

from .serializers import ServiceListSerializer, ServiceSerializer


class ServicePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user

        # Nobody can delete a service
        if request.method == "DELETE":
            return False

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
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ServiceSerializer
    permission_classes = [ServicePermission]

    lookup_field = "slug"

    def get_my_services(self, user):
        if not user or not user.is_authenticated:
            return Service.objects.none()
        if user.is_staff:
            return Service.objects.all()
        return Service.objects.filter(structure__membership__user=user)

    def get_queryset(self):
        qs = None
        user = self.request.user
        only_mine = self.request.query_params.get("mine")

        if only_mine:
            qs = self.get_my_services(user)
        # Everybody can see published services
        elif not user or not user.is_authenticated:
            qs = Service.objects.filter(is_draft=False)
        # Staff can see everything
        elif user.is_staff:
            qs = Service.objects.all()
        else:
            # Authentified users can see everything in their structure
            # plus published services for other structures
            qs = Service.objects.filter(
                Q(is_draft=False) | Q(structure__membership__user=user)
            )
        return qs.order_by("-modification_date")

    def get_serializer_class(self):
        if self.action == "list":
            return ServiceListSerializer
        return super().get_serializer_class()

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

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user, last_editor=self.request.user)

    def perform_update(self, serializer):
        serializer.save(last_editor=self.request.user)


@api_view()
@permission_classes([permissions.AllowAny])
def options(request):
    class AccessConditionSerializer(serializers.ModelSerializer):
        value = serializers.IntegerField(source="id")
        label = serializers.CharField(source="name")

        class Meta:
            model = AccessCondition
            fields = ["value", "label"]

    class ConcernedPublicSerializer(serializers.ModelSerializer):
        value = serializers.IntegerField(source="id")
        label = serializers.CharField(source="name")

        class Meta:
            model = ConcernedPublic
            fields = ["value", "label"]

    class RequirementSerializer(serializers.ModelSerializer):
        value = serializers.IntegerField(source="id")
        label = serializers.CharField(source="name")

        class Meta:
            model = Requirement
            fields = ["value", "label"]

    class CredentialSerializer(serializers.ModelSerializer):
        value = serializers.IntegerField(source="id")
        label = serializers.CharField(source="name")

        class Meta:
            model = Credential
            fields = ["value", "label"]

    result = {
        "categories": [
            {"value": c[0], "label": c[1]} for c in ServiceCategories.choices
        ],
        "subcategories": [
            {"value": c[0], "label": c[1]} for c in ServiceSubCategories.choices
        ],
        "kinds": [{"value": c[0], "label": c[1]} for c in ServiceKind.choices],
        "access_conditions": AccessConditionSerializer(
            AccessCondition.objects.all(), many=True, context={"request": request}
        ).data,
        "concerned_public": ConcernedPublicSerializer(
            ConcernedPublic.objects.all(), many=True, context={"request": request}
        ).data,
        "requirements": RequirementSerializer(
            Requirement.objects.all(), many=True, context={"request": request}
        ).data,
        "credentials": CredentialSerializer(
            Credential.objects.all(), many=True, context={"request": request}
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
        "recurrence": [{"value": c[0], "label": c[1]} for c in RecurrenceKind.choices],
    }
    return Response(result)


class DistanceServiceSerializer(ServiceSerializer):
    distance = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            "category_display",
            "city",
            "distance",
            "name",
            "postal_code",
            "short_desc",
            "slug",
            "structure_info",
            "structure",
        ]

    def get_distance(self, obj):
        if hasattr(obj, "distance"):
            return int(obj.distance.km)
        return None


@api_view()
@permission_classes([permissions.AllowAny])
def search(request):
    category = request.GET.get("cat")
    subcategory = request.GET.get("sub")
    city_code = request.GET.get("city")
    radius = request.GET.get("radius", settings.DEFAULT_SEARCH_RADIUS)

    results = Service.objects.filter(category=category, is_draft=False)
    if subcategory:
        results = results.filter(subcategories__contains=[subcategory])

    if city_code:
        city = get_object_or_404(City, pk=city_code)
        results = (
            results.filter(geom__isnull=False)
            .annotate(distance=Distance("geom", city.geom))
            .filter(distance__lt=D(km=radius))
            .order_by("distance")
        )

    return Response(
        DistanceServiceSerializer(results, many=True, context={"request": request}).data
    )
