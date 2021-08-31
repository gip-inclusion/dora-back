from django.shortcuts import get_object_or_404
from rest_framework import permissions, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from dora.structures.models import Structure, StructureTypology

from .serializers import (
    SiretClaimedSerializer,
    StructureListSerializer,
    StructureSerializer,
)


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

    def get_serializer_class(self):
        if self.action == "list":
            return StructureListSerializer
        return super().get_serializer_class()


@api_view()
@permission_classes([permissions.AllowAny])
def siret_was_claimed(request, siret):
    structure = get_object_or_404(Structure.objects.all(), siret=siret)
    serializer = SiretClaimedSerializer(structure)
    return Response(serializer.data)


@api_view()
@permission_classes([permissions.AllowAny])
def options(request):

    result = {
        "typologies": [
            {"value": c[0], "label": c[1]} for c in StructureTypology.choices
        ],
    }
    return Response(result)
