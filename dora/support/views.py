from rest_framework import mixins, permissions, viewsets

from dora.core.pagination import OptionalPageNumberPagination
from dora.services.enums import ServiceStatus
from dora.services.models import Service
from dora.structures.models import Structure
from dora.support.serializers import (
    ServiceAdminListSerializer,
    ServiceAdminSerializer,
    StructureAdminListSerializer,
    StructureAdminSerializer,
)


class StructureAdminPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if request.method in permissions.SAFE_METHODS:
            return user and user.is_authenticated and user.is_staff
        return False


class ServiceAdminPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if request.method in permissions.SAFE_METHODS:
            return user and user.is_authenticated and user.is_staff
        return False


class StructureAdminViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = StructureAdminSerializer
    permission_classes = [StructureAdminPermission]
    pagination_class = OptionalPageNumberPagination

    lookup_field = "slug"

    def get_queryset(self):
        return Structure.objects.select_related("typology").all()

    def get_serializer_class(self):
        if self.action == "list":
            return StructureAdminListSerializer
        return super().get_serializer_class()


class ServiceAdminViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ServiceAdminSerializer
    permission_classes = [ServiceAdminPermission]
    pagination_class = OptionalPageNumberPagination

    lookup_field = "slug"

    def get_queryset(self):
        return Service.objects.select_related("structure").filter(
            status=ServiceStatus.PUBLISHED
        )

    def get_serializer_class(self):
        if self.action == "list":
            return ServiceAdminListSerializer
        return super().get_serializer_class()
