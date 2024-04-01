from django.conf import settings
from django.db.models import Q
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from rest_framework import permissions, viewsets
from rest_framework.renderers import JSONRenderer
from rest_framework.versioning import NamespaceVersioning

from dora.core.pagination import OptionalPageNumberPagination
from dora.services.models import (
    Service,
)
from dora.structures.models import Structure

from .serializers import (
    ServiceSerializer,
    StructureSerializer,
)


class PrettyCamelCaseJSONRenderer(CamelCaseJSONRenderer):
    def render(self, data, media_type=None, renderer_context=None):
        renderer_context = renderer_context or {}
        renderer_context["indent"] = 4
        return super().render(data, media_type, renderer_context)


############
# V2
############


class APIPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            user.is_authenticated
            and user.email == settings.DATA_INCLUSION_EMAIL
            and request.method in permissions.SAFE_METHODS
        )

    def has_object_permission(self, request, view, service):
        user = request.user
        return (
            user.is_authenticated
            and user.email == settings.DATA_INCLUSION_EMAIL
            and request.method in permissions.SAFE_METHODS
        )


class PrettyJSONRenderer(JSONRenderer):
    def render(self, data, media_type=None, renderer_context=None):
        renderer_context = renderer_context or {}
        renderer_context["indent"] = 4
        return super().render(data, media_type, renderer_context)


class StructureViewSet(viewsets.ReadOnlyModelViewSet):
    versioning_class = NamespaceVersioning
    permission_classes = [APIPermission]
    serializer_class = StructureSerializer
    renderer_classes = [PrettyJSONRenderer]
    pagination_class = OptionalPageNumberPagination

    def get_queryset(self):
        structures = (
            Structure.objects.select_related("typology", "source")
            .prefetch_related("national_labels")
            .all()
        )
        structures = structures.exclude(
            Q(membership=None) & Q(source__value__startswith="di-")
        )
        return structures.order_by("pk")


class ServiceViewSet(viewsets.ReadOnlyModelViewSet):
    versioning_class = NamespaceVersioning
    queryset = (
        Service.objects.published()
        .select_related("structure", "fee_condition")
        .prefetch_related("subcategories", "kinds")
        .order_by("pk")
    )
    serializer_class = ServiceSerializer
    permission_classes = [APIPermission]
    renderer_classes = [PrettyJSONRenderer]
    pagination_class = OptionalPageNumberPagination
