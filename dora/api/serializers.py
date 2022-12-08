from django.conf import settings

# from django.core.files.storage import default_storage
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

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


class StructureTypologySerializer(serializers.ModelSerializer):
    class Meta:
        model = StructureTypology
        fields = ["value", "label"]
        read_only_fields = ["value", "label"]


class StructureSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = StructureSource
        fields = ["value", "label"]
        read_only_fields = ["value", "label"]


class StructureSerializer(serializers.ModelSerializer):
    typology = StructureTypologySerializer(read_only=True)
    source = StructureSourceSerializer(read_only=True)
    creation_date = serializers.DateTimeField(format="%Y-%m-%d", read_only=True)
    modification_date = serializers.DateTimeField(format="%Y-%m-%d", read_only=True)
    link_on_source = serializers.SerializerMethodField()
    services = serializers.HyperlinkedRelatedField(
        many=True, read_only=True, view_name="service-detail"
    )

    class Meta:
        model = Structure
        read_only_fields = [
            "name",
            "short_desc",
            "postal_code",
            "city",
            "address1",
        ]
        fields = [
            "address1",
            "address2",
            "ape",
            "city",
            "city_code",
            "code_safir_pe",
            "creation_date",
            "department",
            "email",
            "full_desc",
            "id",
            "latitude",
            "link_on_source",
            "longitude",
            "modification_date",
            "name",
            "phone",
            "postal_code",
            "services",
            "short_desc",
            "siret",
            "source",
            "typology",
            "url",
        ]

    def get_link_on_source(self, obj) -> str:
        return f"{settings.FRONTEND_URL}/structures/{obj.slug}"


class StringListField(serializers.ListField):
    child = serializers.CharField()


class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ["value", "label"]
        read_only_fields = ["value", "label"]


class ServiceSubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceSubCategory
        fields = ["value", "label"]
        read_only_fields = ["value", "label"]


class ServiceKindSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceKind
        fields = ["value", "label"]
        read_only_fields = ["value", "label"]


class BeneficiaryAccessModeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BeneficiaryAccessMode
        fields = ["value", "label"]
        read_only_fields = ["value", "label"]


class CoachOrientationModeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoachOrientationMode
        fields = ["value", "label"]
        read_only_fields = ["value", "label"]


class LocationKindSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationKind
        fields = ["value", "label"]
        read_only_fields = ["value", "label"]


class ServiceSerializer(serializers.ModelSerializer):
    categories = ServiceCategorySerializer(read_only=True, many=True)
    subcategories = ServiceSubCategorySerializer(read_only=True, many=True)
    kinds = ServiceKindSerializer(read_only=True, many=True)
    access_conditions = serializers.SerializerMethodField()
    concerned_public = serializers.SerializerMethodField()
    beneficiaries_access_modes = BeneficiaryAccessModeSerializer(
        read_only=True, many=True
    )
    coach_orientation_modes = CoachOrientationModeSerializer(read_only=True, many=True)
    requirements = serializers.SerializerMethodField()
    credentials = serializers.SerializerMethodField()
    # forms = serializers.SerializerMethodField()
    location_kinds = LocationKindSerializer(read_only=True, many=True)
    longitude = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()
    diffusion_zone_type = serializers.CharField(
        source="get_diffusion_zone_type_display", read_only=True
    )
    structure = serializers.HyperlinkedRelatedField(
        view_name="structure-detail", read_only=True
    )
    creation_date = serializers.DateTimeField(format="%Y-%m-%d", read_only=True)
    modification_date = serializers.DateTimeField(format="%Y-%m-%d", read_only=True)
    publication_date = serializers.DateTimeField(format="%Y-%m-%d", read_only=True)

    link_on_source = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            "access_conditions",
            "address1",
            "address2",
            "beneficiaries_access_modes",
            "beneficiaries_access_modes_other",
            "categories",
            "city",
            "city_code",
            "coach_orientation_modes",
            "coach_orientation_modes_other",
            "concerned_public",
            "creation_date",
            "credentials",
            "diffusion_zone_details",
            "diffusion_zone_type",
            "fee_condition",
            "fee_details",
            "full_desc",
            "id",
            "is_cumulative",
            "kinds",
            "latitude",
            "link_on_source",
            "location_kinds",
            "longitude",
            "modification_date",
            "name",
            "online_form",
            "postal_code",
            "publication_date",
            "qpv_or_zrr",
            "recurrence",
            "remote_url",
            "requirements",
            "short_desc",
            "structure",
            "subcategories",
            "suspension_date",
        ]
        read_only_fields = ["name"]

    @extend_schema_field(
        StringListField(
            label="Critères d’admission",
            help_text="",
        )
    )
    def get_link_on_source(self, obj) -> str:
        return f"{settings.FRONTEND_URL}/services/{obj.slug}"

    @extend_schema_field(
        StringListField(
            label="Critères d’admission",
            help_text="",
        )
    )
    def get_access_conditions(self, obj) -> list[str]:
        return [item.name for item in obj.access_conditions.all()]

    @extend_schema_field(
        StringListField(
            label="Publics concernés",
            help_text="",
        )
    )
    def get_concerned_public(self, obj) -> list[str]:
        return [item.name for item in obj.concerned_public.all()]

    @extend_schema_field(
        StringListField(
            label="Quels sont les pré-requis ou compétences ?",
            help_text="",
        )
    )
    def get_requirements(self, obj) -> list[str]:
        return [item.name for item in obj.requirements.all()]

    @extend_schema_field(
        StringListField(
            label="Quels sont les justificatifs à fournir ?",
            help_text="",
        )
    )
    def get_credentials(self, obj) -> list[str]:
        return [item.name for item in obj.credentials.all()]

    # @extend_schema_field(
    #     StringListField(
    #         label="Partagez les documents à compléter",
    #         help_text="",
    #     )
    # )
    # def get_forms(self, obj) -> list[str]:
    #     forms = [default_storage.url(form) for form in obj.forms]
    #     return forms

    @extend_schema_field(
        serializers.FloatField(
            label="",
            help_text="Longitude (WGS84)<br>ex: 2.3522",
        )
    )
    def get_longitude(self, obj) -> float:
        return obj.geom.x if obj.geom else None

    @extend_schema_field(
        serializers.FloatField(
            label="",
            help_text="Latitude (WGS84)<br>ex: 48.8566",
        )
    )
    def get_latitude(self, obj) -> float:
        return obj.geom.y if obj.geom else None
