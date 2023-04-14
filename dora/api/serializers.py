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

############
# V2
############


class StructureSerializer(serializers.ModelSerializer):
    accessibilite = serializers.SerializerMethodField()
    adresse = serializers.SerializerMethodField()
    antenne = serializers.SerializerMethodField()
    code_insee = serializers.SerializerMethodField()
    code_postal = serializers.SerializerMethodField()
    commune = serializers.SerializerMethodField()
    complement_adresse = serializers.SerializerMethodField()
    courriel = serializers.SerializerMethodField()
    date_maj = serializers.SerializerMethodField()
    horaires_ouverture = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()
    labels_autres = serializers.SerializerMethodField()
    labels_nationaux = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()
    lien_source = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    nom = serializers.SerializerMethodField()
    presentation_detail = serializers.SerializerMethodField()
    presentation_resume = serializers.SerializerMethodField()
    rna = serializers.SerializerMethodField()
    siret = serializers.SerializerMethodField()
    site_web = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()
    telephone = serializers.SerializerMethodField()
    thematiques = serializers.SerializerMethodField()
    typologie = serializers.SerializerMethodField()

    class Meta:
        model = Structure

        fields = [
            "accessibilite",
            "adresse",
            "antenne",
            "code_insee",
            "code_postal",
            "commune",
            "complement_adresse",
            "courriel",
            "date_maj",
            "horaires_ouverture",
            "id",
            "labels_autres",
            "labels_nationaux",
            "latitude",
            "lien_source",
            "longitude",
            "nom",
            "presentation_detail",
            "presentation_resume",
            "rna",
            "siret",
            "site_web",
            "source",
            "telephone",
            "thematiques",
            "typologie",
        ]

    def get_accessibilite(self, obj):
        return obj.accesslibre_url or None

    def get_adresse(self, obj):
        return obj.address1 or None

    def get_antenne(self, obj) -> bool:
        return obj.parent_id is not None

    def get_code_insee(self, obj):
        return obj.city_code or None

    def get_code_postal(self, obj):
        return obj.postal_code or None

    def get_commune(self, obj):
        return obj.city or None

    def get_complement_adresse(self, obj):
        return obj.address2 or None

    def get_courriel(self, obj):
        return obj.email or None

    def get_date_maj(self, obj):
        return obj.modification_date or None

    def get_horaires_ouverture(self, obj) -> str:
        oh = obj.opening_hours
        dets = obj.opening_hours_details
        if oh:
            if dets:
                return f'{oh}; "{dets}"'
            return oh
        elif dets:
            return f'"{dets}"'
        return None

    def get_id(self, obj):
        return str(obj.id)

    def get_labels_autres(self, obj):
        return obj.other_labels.split(",") if obj.other_labels else []

    def get_labels_nationaux(self, obj):
        return [label.value for label in obj.national_labels.all()]

    def get_latitude(self, obj):
        return obj.latitude

    def get_lien_source(self, obj) -> str:
        return f"{settings.FRONTEND_URL}/structures/{obj.slug}"

    def get_longitude(self, obj):
        return obj.longitude

    def get_nom(self, obj):
        return obj.name or None

    def get_presentation_detail(self, obj):
        return obj.full_desc or None

    def get_presentation_resume(self, obj):
        return obj.short_desc or None

    def get_rna(self, obj):
        return None

    def get_siret(self, obj):
        return obj.siret or None

    def get_site_web(self, obj):
        return obj.url or None

    def get_source(self, obj):
        return obj.source.value if obj.source else None

    def get_telephone(self, obj):
        return obj.phone or None

    def get_thematiques(self, obj) -> [str]:
        cats = set()
        for service in obj.published_services:
            cats |= set(c.value for c in service.subcategories.all())
        return sorted(list(cats))

    def get_typologie(self, obj):
        return obj.typology.value if obj.typology else None


class ServiceSerializer(serializers.ModelSerializer):
    frais = serializers.SerializerMethodField()
    frais_autres = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()
    nom = serializers.SerializerMethodField()
    presentation_resume = serializers.SerializerMethodField()
    prise_rdv = serializers.SerializerMethodField()
    profils = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()
    structure_id = serializers.SerializerMethodField()
    thematiques = serializers.SerializerMethodField()
    types = serializers.SerializerMethodField()

    class Meta:
        model = Service

        fields = [
            "frais",
            "frais_autres",
            "id",
            "nom",
            "presentation_resume",
            "prise_rdv",
            "profils",
            "source",
            "structure_id",
            "thematiques",
            "types",
        ]

    def get_frais(self, obj):
        return obj.fee_condition.value if obj.fee_condition else None

    def get_frais_autres(self, obj):
        return obj.fee_details or None

    def get_id(self, obj):
        return str(obj.id)

    def get_nom(self, obj):
        return obj.name

    def get_presentation_resume(self, obj):
        return obj.short_desc or None

    def get_prise_rdv(self, obj):
        # TODO: pas encore supporté sur DORA
        return None

    def get_profils(self, obj):
        # TODO: mapping DORA à faire
        return None

    def get_source(self, obj):
        # TODO: on n'a pas de notion de source pour les services dans DORA
        return None

    def get_structure_id(self, obj):
        return str(obj.structure_id)

    def get_thematiques(self, obj):
        return [scat.value for scat in obj.subcategories.all()]

    def get_types(self, obj):
        return [k.value for k in obj.kinds.all()]


############
# V1
############


class StructureTypologySerializerV1(serializers.ModelSerializer):
    class Meta:
        model = StructureTypology
        fields = ["value", "label"]
        read_only_fields = ["value", "label"]


class StructureSourceSerializerV1(serializers.ModelSerializer):
    class Meta:
        model = StructureSource
        fields = ["value", "label"]
        read_only_fields = ["value", "label"]


class StructureSerializerV1(serializers.ModelSerializer):
    typology = StructureTypologySerializerV1(read_only=True)
    source = StructureSourceSerializerV1(read_only=True)
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


class ServiceCategorySerializerV1(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ["value", "label"]
        read_only_fields = ["value", "label"]


class ServiceSubCategorySerializerV1(serializers.ModelSerializer):
    class Meta:
        model = ServiceSubCategory
        fields = ["value", "label"]
        read_only_fields = ["value", "label"]


class ServiceKindSerializerV1(serializers.ModelSerializer):
    class Meta:
        model = ServiceKind
        fields = ["value", "label"]
        read_only_fields = ["value", "label"]


class BeneficiaryAccessModeSerializerV1(serializers.ModelSerializer):
    class Meta:
        model = BeneficiaryAccessMode
        fields = ["value", "label"]
        read_only_fields = ["value", "label"]


class CoachOrientationModeSerializerV1(serializers.ModelSerializer):
    class Meta:
        model = CoachOrientationMode
        fields = ["value", "label"]
        read_only_fields = ["value", "label"]


class LocationKindSerializerV1(serializers.ModelSerializer):
    class Meta:
        model = LocationKind
        fields = ["value", "label"]
        read_only_fields = ["value", "label"]


class ServiceSerializerV1(serializers.ModelSerializer):
    categories = ServiceCategorySerializerV1(read_only=True, many=True)
    subcategories = ServiceSubCategorySerializerV1(read_only=True, many=True)
    kinds = ServiceKindSerializerV1(read_only=True, many=True)
    access_conditions = serializers.SerializerMethodField()
    concerned_public = serializers.SerializerMethodField()
    beneficiaries_access_modes = BeneficiaryAccessModeSerializerV1(
        read_only=True, many=True
    )
    coach_orientation_modes = CoachOrientationModeSerializerV1(
        read_only=True, many=True
    )
    requirements = serializers.SerializerMethodField()
    credentials = serializers.SerializerMethodField()
    # forms = serializers.SerializerMethodField()
    location_kinds = LocationKindSerializerV1(read_only=True, many=True)
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
