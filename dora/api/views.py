from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from rest_framework import permissions, viewsets

from dora.services.models import Service
from dora.structures.models import Structure

from .serializers import ServiceSerializer, StructureSerializer


class PrettyCamelCaseJSONRenderer(CamelCaseJSONRenderer):
    def render(self, data, media_type=None, renderer_context=None):
        renderer_context = renderer_context or {}
        renderer_context["indent"] = 4
        return super().render(data, media_type, renderer_context)


class StructureViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Structure.objects.all()
    serializer_class = StructureSerializer
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]


class ServiceViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Service.objects.filter(is_draft=False, is_suggestion=False)
    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]

    renderer_classes = [PrettyCamelCaseJSONRenderer]
