from rest_framework import permissions, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from dora.services.models import (
    Service,
    ServiceCategories,
    ServiceKind,
    ServiceSubCategories,
)

from .serializers import ServiceSerializer


class ServicePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.method in permissions.SAFE_METHODS
            or request.user
            and request.user.is_authenticated
        )


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [ServicePermission]
    lookup_field = "slug"


@api_view()
@permission_classes([permissions.AllowAny])
def options(request):
    result = {
        "categories": ServiceCategories.choices,
        "sub_categories": ServiceSubCategories.choices,
        "kinds": ServiceKind.choices,
    }
    return Response(result)


@api_view()
@permission_classes([permissions.AllowAny])
def search(request):
    category = request.GET.get("cat")
    subcategory = request.GET.get("subcat")
    # city_code = request.GET.get("city")
    results = Service.objects.filter(categories__contains=[category])
    if subcategory:
        results = results.filter(subcategories__contains=[subcategory])

    return Response(ServiceSerializer(results, many=True).data)
