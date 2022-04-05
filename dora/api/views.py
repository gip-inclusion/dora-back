import django_filters
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, permissions, viewsets
from rest_framework.versioning import NamespaceVersioning

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


############
# Structures
############


class StructureFilter(django_filters.FilterSet):
    source = django_filters.ModelChoiceFilter(
        queryset=StructureSource.objects.all(),
        to_field_name="value",
    )

    typology = django_filters.ModelChoiceFilter(
        queryset=StructureTypology.objects.all(),
        to_field_name="value",
    )

    creation_date = django_filters.DateFromToRangeFilter()
    modification_date = django_filters.DateFromToRangeFilter()

    o = django_filters.OrderingFilter(fields=("creation_date", "modificationDate"))

    class Meta:
        model = Structure
        fields = ["department", "siret"]


@extend_schema(tags=["Structures"])
class StructureViewSet(viewsets.ReadOnlyModelViewSet):
    versioning_class = NamespaceVersioning
    queryset = Structure.objects.select_related("typology", "source").all()
    serializer_class = StructureSerializer
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]
    filterset_class = StructureFilter


@extend_schema(tags=["Dictionnaires des structures"])
class StructureTypologyViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    versioning_class = NamespaceVersioning
    queryset = StructureTypology.objects.all()
    serializer_class = StructureTypologySerializer
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]


@extend_schema(tags=["Dictionnaires des structures"])
class StructureSourceViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    versioning_class = NamespaceVersioning
    queryset = StructureSource.objects.all()
    serializer_class = StructureSourceSerializer
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]


##########
# Services
##########


class ServiceFilter(django_filters.FilterSet):
    siret = django_filters.CharFilter(
        field_name="structure__siret",
    )
    structure = django_filters.ModelChoiceFilter(queryset=Structure.objects.all())
    department = django_filters.CharFilter(
        field_name="structure__department",
    )
    creation_date = django_filters.DateFromToRangeFilter()
    modification_date = django_filters.DateFromToRangeFilter()
    categories = django_filters.ModelMultipleChoiceFilter(
        field_name="categories__value",
        queryset=ServiceCategory.objects.all(),
        to_field_name="value",
    )

    o = django_filters.OrderingFilter(fields=("creation_date", "modification_date"))

    class Meta:
        model = Service
        fields = []


@extend_schema(tags=["Services"])
class ServiceViewSet(viewsets.ReadOnlyModelViewSet):
    versioning_class = NamespaceVersioning
    queryset = (
        Service.objects.select_related("structure")
        .prefetch_related(
            "kinds",
            "categories",
            "subcategories",
            "access_conditions",
            "concerned_public",
            "beneficiaries_access_modes",
            "coach_orientation_modes",
            "requirements",
            "credentials",
            "location_kinds",
        )
        .filter(is_draft=False, is_suggestion=False)
    )
    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]
    filterset_class = ServiceFilter


@extend_schema(tags=["Dictionnaires des services"])
class ServiceCategoryViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    versioning_class = NamespaceVersioning
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]


@extend_schema(tags=["Dictionnaires des services"])
class ServiceSubCategoryViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    versioning_class = NamespaceVersioning
    queryset = ServiceSubCategory.objects.all()
    serializer_class = ServiceSubCategorySerializer
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]


@extend_schema(tags=["Dictionnaires des services"])
class ServiceKindViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    versioning_class = NamespaceVersioning
    queryset = ServiceKind.objects.all()
    serializer_class = ServiceKindSerializer
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]


@extend_schema(tags=["Dictionnaires des services"])
class BeneficiaryAccessModeViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    versioning_class = NamespaceVersioning
    queryset = BeneficiaryAccessMode.objects.all()
    serializer_class = BeneficiaryAccessModeSerializer
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]


@extend_schema(tags=["Dictionnaires des services"])
class CoachOrientationModeViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    versioning_class = NamespaceVersioning
    queryset = CoachOrientationMode.objects.all()
    serializer_class = CoachOrientationModeSerializer
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]


@extend_schema(tags=["Dictionnaires des services"])
class LocationKindViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    versioning_class = NamespaceVersioning
    queryset = LocationKind.objects.all()
    serializer_class = LocationKindSerializer
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]
