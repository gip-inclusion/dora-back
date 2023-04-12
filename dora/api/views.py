import django_filters
from django.db.models import Prefetch
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, permissions, viewsets
from rest_framework.renderers import JSONRenderer
from rest_framework.versioning import NamespaceVersioning

from dora.core.pagination import OptionalPageNumberPagination
from dora.services.enums import ServiceStatus
from dora.services.models import (
    BeneficiaryAccessMode,
    CoachOrientationMode,
    LocationKind,
    Service,
    ServiceCategory,
    ServiceKind,
    ServiceSubCategory,
)
from dora.services.utils import (
    filter_services_by_city_code,
    filter_services_by_department,
    filter_services_by_region,
)
from dora.structures.models import Structure, StructureSource, StructureTypology

from .serializers import (
    BeneficiaryAccessModeSerializerV1,
    CoachOrientationModeSerializerV1,
    LocationKindSerializerV1,
    ServiceCategorySerializerV1,
    ServiceKindSerializerV1,
    ServiceSerializer,
    ServiceSerializerV1,
    ServiceSubCategorySerializerV1,
    StructureSerializer,
    StructureSerializerV1,
    StructureSourceSerializerV1,
    StructureTypologySerializerV1,
)


class PrettyCamelCaseJSONRenderer(CamelCaseJSONRenderer):
    def render(self, data, media_type=None, renderer_context=None):
        renderer_context = renderer_context or {}
        renderer_context["indent"] = 4
        return super().render(data, media_type, renderer_context)


############
# V2
############


class PrettyJSONRenderer(JSONRenderer):
    def render(self, data, media_type=None, renderer_context=None):
        renderer_context = renderer_context or {}
        renderer_context["indent"] = 4
        return super().render(data, media_type, renderer_context)


class StructureViewSet(viewsets.ReadOnlyModelViewSet):
    versioning_class = NamespaceVersioning
    queryset = (
        Structure.objects.select_related("typology", "source")
        .prefetch_related(
            "national_labels",
            Prefetch(
                "services",
                queryset=Service.objects.filter(status=ServiceStatus.PUBLISHED),
                to_attr="published_services",
            ),
            "published_services__subcategories",
        )
        .all()
    )
    permission_classes = [permissions.AllowAny]
    serializer_class = StructureSerializer
    renderer_classes = [PrettyJSONRenderer]
    pagination_class = OptionalPageNumberPagination


class ServiceViewSet(viewsets.ReadOnlyModelViewSet):
    versioning_class = NamespaceVersioning
    queryset = (
        Service.objects.published()
        .select_related("structure", "fee_condition")
        .prefetch_related("subcategories", "kinds")
    )
    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyJSONRenderer]
    pagination_class = OptionalPageNumberPagination


############
# V1
############


class StructureFilterV1(django_filters.FilterSet):
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

    o = django_filters.OrderingFilter(fields=("creation_date", "modification_date"))

    class Meta:
        model = Structure
        fields = ["department", "siret"]


@extend_schema(
    tags=["Structures"],
)
class StructureViewSetV1(viewsets.ReadOnlyModelViewSet):
    versioning_class = NamespaceVersioning
    queryset = Structure.objects.select_related("typology", "source").all()
    serializer_class = StructureSerializerV1
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]
    filterset_class = StructureFilterV1
    pagination_class = OptionalPageNumberPagination


@extend_schema(tags=["Dictionnaires des structures"])
class StructureTypologyViewSetV1(mixins.ListModelMixin, viewsets.GenericViewSet):
    versioning_class = NamespaceVersioning
    queryset = StructureTypology.objects.all()
    serializer_class = StructureTypologySerializerV1
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]


@extend_schema(tags=["Dictionnaires des structures"])
class StructureSourceViewSetV1(mixins.ListModelMixin, viewsets.GenericViewSet):
    versioning_class = NamespaceVersioning
    queryset = StructureSource.objects.all()
    serializer_class = StructureSourceSerializerV1
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]


class ServiceFilterV1(django_filters.FilterSet):
    siret = django_filters.CharFilter(
        field_name="structure__siret",
    )
    structure = django_filters.ModelChoiceFilter(queryset=Structure.objects.all())
    creation_date = django_filters.DateFromToRangeFilter()
    modification_date = django_filters.DateFromToRangeFilter()
    categories = django_filters.ModelMultipleChoiceFilter(
        field_name="categories__value",
        queryset=ServiceCategory.objects.all(),
        to_field_name="value",
    )
    subcategories = django_filters.ModelMultipleChoiceFilter(
        field_name="subcategories__value",
        queryset=ServiceSubCategory.objects.all(),
        to_field_name="value",
    )
    city = django_filters.CharFilter(
        method="filter_by_city_code", help_text="Code INSEE de la commune"
    )
    department = django_filters.CharFilter(
        method="filter_by_department_code", help_text="Code INSEE du département"
    )
    region = django_filters.CharFilter(
        method="filter_by_region_code", help_text="Code INSEE de la région"
    )

    o = django_filters.OrderingFilter(
        fields=("creation_date", "modification_date", "name")
    )

    class Meta:
        model = Service
        fields = []

    def filter_by_city_code(self, queryset, _name, city_code):
        return filter_services_by_city_code(queryset, city_code)

    def filter_by_department_code(self, queryset, _name, dept_code):
        return filter_services_by_department(queryset, dept_code)

    def filter_by_region_code(self, queryset, _name, region_code):
        return filter_services_by_region(queryset, region_code)


@extend_schema(tags=["Services"])
class ServiceViewSetV1(viewsets.ReadOnlyModelViewSet):
    versioning_class = NamespaceVersioning
    queryset = (
        Service.objects.published()
        .select_related("structure")
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
    )
    serializer_class = ServiceSerializerV1
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]
    filterset_class = ServiceFilterV1
    pagination_class = OptionalPageNumberPagination


@extend_schema(tags=["Dictionnaires des services"])
class ServiceCategoryViewSetV1(mixins.ListModelMixin, viewsets.GenericViewSet):
    versioning_class = NamespaceVersioning
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializerV1
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]


@extend_schema(tags=["Dictionnaires des services"])
class ServiceSubCategoryViewSetV1(mixins.ListModelMixin, viewsets.GenericViewSet):
    versioning_class = NamespaceVersioning
    queryset = ServiceSubCategory.objects.all()
    serializer_class = ServiceSubCategorySerializerV1
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]


@extend_schema(tags=["Dictionnaires des services"])
class ServiceKindViewSetV1(mixins.ListModelMixin, viewsets.GenericViewSet):
    versioning_class = NamespaceVersioning
    queryset = ServiceKind.objects.all()
    serializer_class = ServiceKindSerializerV1
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]


@extend_schema(tags=["Dictionnaires des services"])
class BeneficiaryAccessModeViewSetV1(mixins.ListModelMixin, viewsets.GenericViewSet):
    versioning_class = NamespaceVersioning
    queryset = BeneficiaryAccessMode.objects.all()
    serializer_class = BeneficiaryAccessModeSerializerV1
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]


@extend_schema(tags=["Dictionnaires des services"])
class CoachOrientationModeViewSetV1(mixins.ListModelMixin, viewsets.GenericViewSet):
    versioning_class = NamespaceVersioning
    queryset = CoachOrientationMode.objects.all()
    serializer_class = CoachOrientationModeSerializerV1
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]


@extend_schema(tags=["Dictionnaires des services"])
class LocationKindViewSetV1(mixins.ListModelMixin, viewsets.GenericViewSet):
    versioning_class = NamespaceVersioning
    queryset = LocationKind.objects.all()
    serializer_class = LocationKindSerializerV1
    permission_classes = [permissions.AllowAny]
    renderer_classes = [PrettyCamelCaseJSONRenderer]
