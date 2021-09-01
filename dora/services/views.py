from rest_framework import permissions, serializers, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

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

from .serializers import ServiceListSerializer, ServiceSerializer


class ServicePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.method in permissions.SAFE_METHODS
            or request.user
            and request.user.is_authenticated
        )


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all().order_by("-modification_date")
    serializer_class = ServiceSerializer
    permission_classes = [ServicePermission]
    lookup_field = "slug"

    def get_serializer_class(self):
        if self.action == "list":
            return ServiceListSerializer
        return super().get_serializer_class()


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
            AccessCondition.objects.all(), many=True
        ).data,
        "concerned_public": ConcernedPublicSerializer(
            ConcernedPublic.objects.all(), many=True
        ).data,
        "requirements": RequirementSerializer(
            Requirement.objects.all(), many=True
        ).data,
        "credentials": CredentialSerializer(Credential.objects.all(), many=True).data,
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


@api_view()
@permission_classes([permissions.AllowAny])
def search(request):
    category = request.GET.get("cat")
    subcategory = request.GET.get("subcat")
    # city_code = request.GET.get("city")
    results = Service.objects.filter(category=category)
    if subcategory:
        results = results.filter(subcategories__contains=[subcategory])

    return Response(ServiceSerializer(results, many=True).data)
