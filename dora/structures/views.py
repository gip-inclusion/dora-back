from rest_framework import permissions, viewsets

from dora.structures.models import Structure

from .serializers import StructureSerializer


class StructurePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.method in permissions.SAFE_METHODS
            or request.user
            and request.user.is_authenticated
        )


class StructureViewSet(viewsets.ModelViewSet):
    queryset = Structure.objects.all()
    serializer_class = StructureSerializer
    permission_classes = [StructurePermission]
    lookup_field = "slug"
