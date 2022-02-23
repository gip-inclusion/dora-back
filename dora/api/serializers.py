from asyncio.log import logger

from django.core.files.storage import default_storage
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from dora.services.models import (
    BeneficiaryAccessMode,
    CoachOrientationMode,
    LocationKind,
    Service,
    ServiceKind,
    ServiceSubCategories,
)
from dora.structures.models import Structure


class StructureSerializer(serializers.ModelSerializer):
    typology = serializers.CharField(source="get_typology_display")
    source = serializers.CharField(source="get_source_display")

    class Meta:
        model = Structure
        fields = [
            "siret",
            "code_safir_pe",
            "typology",
            "slug",
            "name",
            "short_desc",
            "full_desc",
            "url",
            # "phone",
            # "email",
            "postal_code",
            "city_code",
            "city",
            "department",
            "address1",
            "address2",
            "ape",
            "longitude",
            "latitude",
            "creation_date",
            "modification_date",
            "source",
        ]


class StringListField(serializers.ListField):
    child = serializers.CharField()


class ServiceSerializer(serializers.ModelSerializer):
    kinds = serializers.SerializerMethodField()
    category = serializers.CharField(source="get_category_display")
    subcategories = serializers.SerializerMethodField()
    access_conditions = serializers.SerializerMethodField()
    concerned_public = serializers.SerializerMethodField()
    beneficiaries_access_modes = serializers.SerializerMethodField()
    coach_orientation_modes = serializers.SerializerMethodField()
    requirements = serializers.SerializerMethodField()
    credentials = serializers.SerializerMethodField()
    forms = serializers.SerializerMethodField()
    location_kinds = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()
    diffusion_zone_type = serializers.CharField(
        source="get_diffusion_zone_type_display"
    )
    structure = serializers.SlugRelatedField(slug_field="siret", read_only=True)

    class Meta:
        model = Service
        fields = [
            "slug",
            "name",
            "short_desc",
            "full_desc",
            "kinds",
            "category",
            "subcategories",
            "access_conditions",
            "concerned_public",
            "is_cumulative",
            "has_fee",
            "fee_details",
            "beneficiaries_access_modes",
            "beneficiaries_access_modes_other",
            "coach_orientation_modes",
            "coach_orientation_modes_other",
            "requirements",
            "credentials",
            "forms",
            "online_form",
            # "contact_name",
            # "contact_phone",
            # "contact_email",
            # "is_contact_info_public",
            "location_kinds",
            "remote_url",
            "address1",
            "address2",
            "postal_code",
            "city_code",
            "city",
            "longitude",
            "latitude",
            "diffusion_zone_type",
            "diffusion_zone_details",
            "qpv_or_zrr",
            "recurrence",
            "suspension_date",
            "structure",
            "creation_date",
            "modification_date",
            "publication_date",
        ]

    @extend_schema_field(
        StringListField(
            label="Type de service",
            help_text="",
        )
    )
    def get_kinds(self, obj):
        return [ServiceKind(kind).label for kind in obj.kinds]

    @extend_schema_field(
        StringListField(
            label="Sous-catégorie",
            help_text="",
        )
    )
    def get_subcategories(self, obj) -> list[str]:
        try:
            return [ServiceSubCategories(cat).label for cat in obj.subcategories]
        except ValueError:
            logger.exception(
                "Incorrect Service sub-category", extra={"values": obj.subcategories}
            )
            return []

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
            label="Comment mobiliser la solution en tant que bénéficiaire",
            help_text="",
        )
    )
    def get_beneficiaries_access_modes(self, obj) -> list[str]:
        return [
            BeneficiaryAccessMode(mode).label for mode in obj.beneficiaries_access_modes
        ]

    @extend_schema_field(
        StringListField(
            label="Comment orienter un bénéficiaire en tant qu’accompagnateur",
            help_text="",
        )
    )
    def get_coach_orientation_modes(self, obj) -> list[str]:
        return [
            CoachOrientationMode(mode).label for mode in obj.coach_orientation_modes
        ]

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

    @extend_schema_field(
        StringListField(
            label="Partagez les documents à compléter",
            help_text="",
        )
    )
    def get_forms(self, obj) -> list[str]:
        forms = [default_storage.url(form) for form in obj.forms]
        return forms

    @extend_schema_field(
        StringListField(
            label="Lieu de déroulement",
            help_text="",
        )
    )
    def get_location_kinds(self, obj) -> list[str]:
        return [LocationKind(kind).label for kind in obj.location_kinds]

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
