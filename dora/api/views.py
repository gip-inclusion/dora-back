from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from rest_framework import mixins, permissions, viewsets

from dora.services.models import (
    BeneficiaryAccessMode,
    CoachOrientationMode,
    LocationKind,
    Service,
    ServiceCategory,
    ServiceKind,
    ServiceSubCategory,
)
from dora.structures.models import Structure, StructureSource, StructureTypology

from .serializers import (
    BeneficiaryAccessModeSerializer,
    CoachOrientationModeSerializer,
    LocationKindSerializer,
    ServiceCategorySerializer,
    ServiceKindSerializer,
    ServiceSerializer,
    ServiceSubCategorySerializer,
    StructureSerializer,
    StructureSourceSerializer,
    StructureTypologySerializer,
)


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
    lookup_field = "slug"


class StructureTypologyViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = StructureTypology.objects.all()
    serializer_class = StructureTypologySerializer
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]


class StructureSourceViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = StructureSource.objects.all()
    serializer_class = StructureSourceSerializer
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]


class ServiceViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Service.objects.filter(is_draft=False, is_suggestion=False)
    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]
    lookup_field = "slug"


class ServiceCategoryViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):

    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]


class ServiceSubCategoryViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):

    queryset = ServiceSubCategory.objects.all()
    serializer_class = ServiceSubCategorySerializer
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]


class ServiceKindViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):

    queryset = ServiceKind.objects.all()
    serializer_class = ServiceKindSerializer
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]


class BeneficiaryAccessModeViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):

    queryset = BeneficiaryAccessMode.objects.all()
    serializer_class = BeneficiaryAccessModeSerializer
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]


class CoachOrientationModeViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):

    queryset = CoachOrientationMode.objects.all()
    serializer_class = CoachOrientationModeSerializer
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]


class LocationKindViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):

    queryset = LocationKind.objects.all()
    serializer_class = LocationKindSerializer
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]
