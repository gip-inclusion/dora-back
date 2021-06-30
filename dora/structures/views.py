from rest_framework import permissions, viewsets

from dora.structures.models import Structure

from .serializers import StructureSerializer


class StructurePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        # Make it read-only for now
        return request.method in permissions.SAFE_METHODS


class StructureViewSet(viewsets.ModelViewSet):
    queryset = Structure.objects.all()
    serializer_class = StructureSerializer
    permission_classes = [StructurePermission]
