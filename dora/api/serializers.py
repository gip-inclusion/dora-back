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
        return obj.other_labels

    def get_labels_nationaux(self, obj):
        return [label.value for label in obj.national_labels.all()]

    def get_latitude(self, obj):
        return obj.latitude

    def get_lien_source(self, obj) -> str:
        return obj.get_frontend_url()

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

    def get_thematiques(self, obj):
        # Les thématiques sont portées par les services
        return None

    def get_typologie(self, obj):
        return obj.typology.value if obj.typology else None


class ServiceSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    structure_id = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()
    nom = serializers.SerializerMethodField()
    presentation_resume = serializers.SerializerMethodField()
    presentation_detail = serializers.SerializerMethodField()
    types = serializers.SerializerMethodField()
    thematiques = serializers.SerializerMethodField()
    prise_rdv = serializers.SerializerMethodField()
    frais = serializers.SerializerMethodField()
    frais_autres = serializers.SerializerMethodField()
    profils = serializers.SerializerMethodField()
    pre_requis = serializers.SerializerMethodField()
    cumulable = serializers.SerializerMethodField()
    justificatifs = serializers.SerializerMethodField()
    formulaire_en_ligne = serializers.SerializerMethodField()
    commune = serializers.SerializerMethodField()
    code_postal = serializers.SerializerMethodField()
    code_insee = serializers.SerializerMethodField()
    adresse = serializers.SerializerMethodField()
    complement_adresse = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()
    recurrence = serializers.SerializerMethodField()
    date_creation = serializers.SerializerMethodField()
    date_maj = serializers.SerializerMethodField()
    date_suspension = serializers.SerializerMethodField()
    lien_source = serializers.SerializerMethodField()
    telephone = serializers.SerializerMethodField()
    courriel = serializers.SerializerMethodField()
    contact_nom = serializers.SerializerMethodField()
    contact_prenom = serializers.SerializerMethodField()
    contact_public = serializers.SerializerMethodField()
    modes_accueil = serializers.SerializerMethodField()
    zone_diffusion_type = serializers.SerializerMethodField()
    zone_diffusion_code = serializers.SerializerMethodField()
    zone_diffusion_nom = serializers.SerializerMethodField()
    modes_orientation_accompagnateur = serializers.SerializerMethodField()
    modes_orientation_accompagnateur_autres = serializers.SerializerMethodField()
    modes_orientation_beneficiaire = serializers.SerializerMethodField()
    modes_orientation_beneficiaire_autres = serializers.SerializerMethodField()

    class Meta:
        model = Service

        fields = [
            "adresse",
            "code_insee",
            "code_postal",
            "commune",
            "complement_adresse",
            "contact_nom",
            "contact_prenom",
            "contact_public",
            "courriel",
            "cumulable",
            "date_creation",
            "date_maj",
            "date_suspension",
            "formulaire_en_ligne",
            "frais_autres",
            "frais",
            "id",
            "justificatifs",
            "latitude",
            "lien_source",
            "longitude",
            "modes_accueil",
            "nom",
            "pre_requis",
            "presentation_detail",
            "presentation_resume",
            "prise_rdv",
            "profils",
            "recurrence",
            "source",
            "structure_id",
            "telephone",
            "thematiques",
            "types",
            "zone_diffusion_code",
            "zone_diffusion_nom",
            "zone_diffusion_type",
            "modes_orientation_accompagnateur",
            "modes_orientation_accompagnateur_autres",
            "modes_orientation_beneficiaire",
            "modes_orientation_beneficiaire_autres",
        ]

    def get_id(self, obj):
        return str(obj.id)

    def get_structure_id(self, obj):
        return str(obj.structure_id)

    def get_source(self, obj):
        return obj.source.value if obj.source else None

    def get_nom(self, obj):
        return obj.name

    def get_presentation_resume(self, obj):
        return obj.short_desc or None

    def get_presentation_detail(self, obj):
        return obj.full_desc or None

    def get_types(self, obj):
        return [k.value for k in obj.kinds.all()]

    def get_thematiques(self, obj):
        scats = [scat.value for scat in obj.subcategories.all()]
        return [scat for scat in scats if not scat.endswith("--autre")]

    def get_prise_rdv(self, obj):
        # TODO: pas encore supporté sur DORA
        return None

    def get_frais(self, obj):
        return obj.fee_condition.value if obj.fee_condition else None

    def get_frais_autres(self, obj):
        return obj.fee_details or None

    def get_profils(self, obj):
        # TODO: mapping DORA à faire
        return [c.name for c in obj.concerned_public.all()]

    def get_pre_requis(self, obj):
        return [c.name for c in obj.requirements.all()]

    def get_cumulable(self, obj):
        return obj.is_cumulative

    def get_justificatifs(self, obj):
        return [c.name for c in obj.credentials.all()]

    def get_formulaire_en_ligne(self, obj):
        return obj.online_form if obj.online_form else None

    def get_commune(self, obj):
        return obj.city if obj.city else None

    def get_code_postal(self, obj):
        return obj.postal_code if obj.postal_code else None

    def get_code_insee(self, obj):
        return obj.city_code if obj.city_code else None

    def get_adresse(self, obj):
        return obj.address1 if obj.address1 else None

    def get_complement_adresse(self, obj):
        return obj.address2 if obj.address2 else None

    def get_longitude(self, obj):
        return obj.geom.x if obj.geom else None

    def get_latitude(self, obj):
        return obj.geom.y if obj.geom else None

    def get_recurrence(self, obj):
        return obj.recurrence if obj.recurrence else None

    def get_date_creation(self, obj):
        return obj.publication_date if obj.publication_date else None

    def get_date_maj(self, obj):
        return obj.modification_date or None

    def get_date_suspension(self, obj):
        return obj.suspension_date if obj.suspension_date else None

    def get_lien_source(self, obj):
        return obj.get_frontend_url()

    def get_telephone(self, obj):
        assert self.context.get("request").user.email == settings.DATA_INCLUSION_EMAIL
        return obj.contact_phone

    def get_courriel(self, obj):
        assert self.context.get("request").user.email == settings.DATA_INCLUSION_EMAIL
        return obj.contact_email

    def get_contact_nom(self, obj):
        assert self.context.get("request").user.email == settings.DATA_INCLUSION_EMAIL
        return obj.contact_name

    def get_contact_prenom(self, obj):
        assert self.context.get("request").user.email == settings.DATA_INCLUSION_EMAIL
        return None

    def get_contact_public(self, obj):
        return obj.is_contact_info_public

    def get_modes_accueil(self, obj):
        return [k.value for k in obj.location_kinds.all()]

    def get_zone_diffusion_type(self, obj):
        if obj.diffusion_zone_type == "city":
            return "commune"
        if obj.diffusion_zone_type == "epci":
            return "epci"
        if obj.diffusion_zone_type == "department":
            return "departement"
        if obj.diffusion_zone_type == "region":
            return "region"
        if obj.diffusion_zone_type == "country":
            return None

    def get_zone_diffusion_code(self, obj):
        return obj.diffusion_zone_details

    def get_zone_diffusion_nom(self, obj):
        return obj.get_diffusion_zone_details_display()

    def get_modes_orientation_accompagnateur(self, obj):
        mapping = {
            "autre": "autre",
            "telephoner": "telephoner",
            "envoyer-formulaire": "completer-le-formulaire-dadhesion",
            "envoyer-courriel": "envoyer-un-mail",
            "envoyer-fiche-prescription": "envoyer-un-mail-avec-une-fiche-de-prescription",
        }  # TODO: à supprimer une fois dora et data.inclusion alignés sur le référentiel
        return [
            mapping.get(mode.value, mode.value)
            for mode in obj.coach_orientation_modes.all()
        ]

    def get_modes_orientation_accompagnateur_autres(self, obj):
        return None

    def get_modes_orientation_beneficiaire(self, obj):
        mapping = {
            "autre": "autre",
            "telephoner": "telephoner",
            "envoyer-courriel": "envoyer-un-mail",
            "se-presenter": "se-presenter",
        }  # TODO: à supprimer une fois dora et data.inclusion alignés sur le référentiel
        return [
            mapping.get(mode.value, mode.value)
            for mode in obj.beneficiaries_access_modes.all()
        ]

    def get_modes_orientation_beneficiaire_autres(self, obj):
        return None


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
    subcategories = serializers.SerializerMethodField()
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

    def get_subcategories(self, obj):
        scats = obj.subcategories.exclude(value__endswith=("--autre"))
        return [{"value": scat.value, "label": scat.label} for scat in scats]
