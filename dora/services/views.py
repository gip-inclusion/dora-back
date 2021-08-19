from rest_framework import permissions, viewsets

from dora.services.models import Service

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
