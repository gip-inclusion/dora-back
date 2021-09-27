from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from dora.core.notify import send_mattermost_notification
from dora.structures.models import Structure, StructureSource, StructureTypology

from .serializers import (
    SiretClaimedSerializer,
    StructureListSerializer,
    StructureSerializer,
)


class StructurePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user

        # Nobody can delete a structure
        if request.method == "DELETE":
            return False

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
        return obj in user_structures


class StructureViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = StructureSerializer
    permission_classes = [StructurePermission]
    lookup_field = "slug"

    def get_queryset(self):
        only_mine = self.request.query_params.get("mine")

        if only_mine:
            user = self.request.user
            if user and user.is_authenticated:
                if user.is_staff:
                    return Structure.objects.all()
                return Structure.objects.filter(membership__user=user)
            else:
                return Structure.objects.none()
        return Structure.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return StructureListSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        user = self.request.user
        source = (
            StructureSource.DORA_STAFF
            if user.is_staff
            else StructureSource.STRUCT_STAFF
        )
        structure = serializer.save(creator=user, last_editor=user, source=source)
        send_mattermost_notification(
            f"[{settings.ENVIRONMENT}] :tada: Nouvelle structure “{structure.name}” créée dans le departement : **{structure.department}**\n{settings.FRONTEND_URL}/structures/{structure.slug}"
        )

    def perform_update(self, serializer):
        serializer.save(last_editor=self.request.user)


@api_view()
@permission_classes([permissions.AllowAny])
def siret_was_claimed(request, siret):
    structure = get_object_or_404(Structure.objects.all(), siret=siret)
    serializer = SiretClaimedSerializer(structure, context={"request": request})
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


@api_view()
@permission_classes([permissions.AllowAny])
def search_safir(request):
    safir_code = request.query_params.get("safir", "")
    if not safir_code:
        return Response("need safir")

    structure = get_object_or_404(Structure, code_safir_pe=safir_code)
    return Response(StructureSerializer(structure, context={"request": request}).data)
