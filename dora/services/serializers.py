import logging

from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from dora.services.enums import ServiceStatus
from rest_framework import serializers
from rest_framework.relations import PrimaryKeyRelatedField

from dora.admin_express.models import EPCI, City, Department, Region
from dora.core.utils import code_insee_to_code_dept
from dora.structures.models import Structure, StructureMember

from .models import (
    AccessCondition,
    AdminDivisionType,
    BeneficiaryAccessMode,
    CoachOrientationMode,
    ConcernedPublic,
    Credential,
    LocationKind,
    Requirement,
    Service,
    ServiceCategory,
    ServiceKind,
    ServiceModel,
    ServiceSubCategory,
)

logger = logging.getLogger(__name__)


class CreatablePrimaryKeyRelatedField(PrimaryKeyRelatedField):
    def __init__(self, **kwargs):
        self.max_length = kwargs.pop("max_length", None)
        super().__init__(**kwargs)

    def use_pk_only_optimization(self):
        return True

    def to_internal_value(self, data):
        if isinstance(data, int):
            return super().to_internal_value(data)

        # If we receive a string instead of a primary key, search
        # by value, and create a new object if not found

        name = data.strip()
        if name == "":
            raise ValidationError("Cette valeur est vide")

        if self.max_length is not None and len(name) > self.max_length:
            raise ValidationError(
                f"Cette valeur doit avoir moins de {self.max_length} caractères"
            )

        if self.root.instance:
            structure = self.root.instance.structure
        else:
            structure_slug = self.root.initial_data["structure"]
            structure = Structure.objects.get(slug=structure_slug)
        if not structure:
            raise ValidationError("La structure ne peut pas être vide")
        queryset = self.queryset

        # find if it already exists in the same structure
        obj = queryset.filter(name=name, structure=structure).first()
        if not obj:
            # then in the global repository
            obj = queryset.filter(name=name, structure=None).first()
        if not obj:
            # otherwise create it
            obj = queryset.create(name=name, structure=structure)
        return obj


# On veut sérialiser le nom du champ pour les valeurs spécifiques à une
# structure, puisque l'utilisateur ne pourra pas la retrouver sur le frontend
# TODO: a simplifier: ça devrait devenir le mécanisme général, même pour
# sérialiser les services. Peut-être qu'on pourrait même toujours sérialiser directement
# les chaines au lieu des ids.
class ModelCreatablePrimaryKeyRelatedField(CreatablePrimaryKeyRelatedField):
    def to_representation(self, value):
        return value.name if value.structure else value.id


class StructureSerializer(serializers.ModelSerializer):
    has_admin = serializers.SerializerMethodField()
    num_services = serializers.SerializerMethodField()

    class Meta:
        model = Structure
        fields = [
            "slug",
            "name",
            "short_desc",
            "address1",
            "address2",
            "postal_code",
            "city",
            "url",
            "siret",
            "has_admin",
            "num_services",
        ]

    def get_has_admin(self, structure):
        return structure.membership.filter(is_admin=True, user__is_staff=False).exists()

    def get_num_services(self, structure):
        return structure.get_num_visible_services(self.context["request"].user)


def _get_diffusion_zone_type_display(obj):
    return (
        AdminDivisionType(obj.diffusion_zone_type).label
        if obj.diffusion_zone_type
        else ""
    )


def _get_diffusion_zone_details_display(obj):
    if obj.diffusion_zone_type == AdminDivisionType.COUNTRY:
        return "France entière"

    if obj.diffusion_zone_type == AdminDivisionType.CITY:
        city = City.objects.get_from_code(obj.diffusion_zone_details)
        # TODO: we'll probably want to log and correct a missing code
        return f"{city.name} ({city.department})" if city else ""

    item = None

    if obj.diffusion_zone_type == AdminDivisionType.EPCI:
        item = EPCI.objects.get_from_code(obj.diffusion_zone_details)
    elif obj.diffusion_zone_type == AdminDivisionType.DEPARTMENT:
        item = Department.objects.get_from_code(obj.diffusion_zone_details)
    elif obj.diffusion_zone_type == AdminDivisionType.REGION:
        item = Region.objects.get_from_code(obj.diffusion_zone_details)
    # TODO: we'll probably want to log and correct a missing code
    return item.name if item else ""


class ServiceSerializer(serializers.ModelSerializer):
    # pour rétrocompatibilité temporaire
    category = serializers.SerializerMethodField()
    category_display = serializers.SerializerMethodField()

    is_available = serializers.SerializerMethodField()
    forms_info = serializers.SerializerMethodField()
    structure = serializers.SlugRelatedField(
        queryset=Structure.objects.all(), slug_field="slug"
    )
    structure_info = StructureSerializer(source="structure", read_only=True)
    kinds = serializers.SlugRelatedField(
        slug_field="value",
        queryset=ServiceKind.objects.all(),
        many=True,
        required=False,
    )
    kinds_display = serializers.SlugRelatedField(
        source="kinds", slug_field="label", many=True, read_only=True
    )
    categories = serializers.SlugRelatedField(
        slug_field="value",
        queryset=ServiceCategory.objects.all(),
        many=True,
        required=False,
    )
    categories_display = serializers.SlugRelatedField(
        source="categories", slug_field="label", many=True, read_only=True
    )
    subcategories = serializers.SlugRelatedField(
        slug_field="value",
        queryset=ServiceSubCategory.objects.all(),
        many=True,
        required=False,
    )
    subcategories_display = serializers.SlugRelatedField(
        source="subcategories", slug_field="label", many=True, read_only=True
    )
    access_conditions = CreatablePrimaryKeyRelatedField(
        many=True,
        queryset=AccessCondition.objects.all(),
        max_length=140,
        required=False,
    )
    access_conditions_display = serializers.SerializerMethodField()
    concerned_public = CreatablePrimaryKeyRelatedField(
        many=True,
        queryset=ConcernedPublic.objects.all(),
        max_length=140,
        required=False,
    )
    concerned_public_display = serializers.SerializerMethodField()
    requirements = CreatablePrimaryKeyRelatedField(
        many=True,
        queryset=Requirement.objects.all(),
        max_length=140,
        required=False,
    )
    requirements_display = serializers.SerializerMethodField()
    credentials = CreatablePrimaryKeyRelatedField(
        many=True,
        queryset=Credential.objects.all(),
        max_length=140,
        required=False,
    )
    credentials_display = serializers.SerializerMethodField()
    location_kinds = serializers.SlugRelatedField(
        slug_field="value",
        queryset=LocationKind.objects.all(),
        many=True,
        required=False,
    )
    location_kinds_display = serializers.SlugRelatedField(
        source="location_kinds", slug_field="label", many=True, read_only=True
    )
    diffusion_zone_type_display = serializers.SerializerMethodField()
    diffusion_zone_details_display = serializers.SerializerMethodField()
    beneficiaries_access_modes = serializers.SlugRelatedField(
        slug_field="value",
        queryset=BeneficiaryAccessMode.objects.all(),
        many=True,
        required=False,
    )
    beneficiaries_access_modes_display = serializers.SlugRelatedField(
        source="beneficiaries_access_modes",
        slug_field="label",
        many=True,
        read_only=True,
    )
    coach_orientation_modes = serializers.SlugRelatedField(
        slug_field="value",
        queryset=CoachOrientationMode.objects.all(),
        many=True,
        required=False,
    )
    coach_orientation_modes_display = serializers.SlugRelatedField(
        source="coach_orientation_modes", slug_field="label", many=True, read_only=True
    )
    department = serializers.SerializerMethodField()
    can_write = serializers.SerializerMethodField()
    eligible_to_tally_form = serializers.SerializerMethodField()

    model_changed = serializers.SerializerMethodField()
    model = serializers.SlugRelatedField(
        queryset=ServiceModel.objects.all(),
        slug_field="slug",
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Service

        fields = [
            "category",
            "category_display",
            "slug",
            "name",
            "short_desc",
            "full_desc",
            "kinds",
            "categories",
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
            "contact_name",
            "contact_phone",
            "contact_email",
            "is_contact_info_public",
            "location_kinds",
            "diffusion_zone_type",
            "diffusion_zone_details",
            "qpv_or_zrr",
            "remote_url",
            "address1",
            "address2",
            "postal_code",
            "city_code",
            "city",
            "geom",
            "recurrence",
            "suspension_date",
            "structure",
            "creation_date",
            "modification_date",
            "status",
            "is_available",
            "forms_info",
            "structure",
            "structure_info",
            "kinds_display",
            "categories_display",
            "subcategories_display",
            "access_conditions_display",
            "concerned_public_display",
            "requirements_display",
            "credentials_display",
            "location_kinds_display",
            "diffusion_zone_type_display",
            "diffusion_zone_details_display",
            "beneficiaries_access_modes_display",
            "coach_orientation_modes_display",
            "department",
            "can_write",
            "model_changed",
            "model",
            "filling_duration",
            "eligible_to_tally_form",
        ]
        lookup_field = "slug"

    def get_category(self, obj):
        # On n'utilise volontairement pas .first() ici pour éviter une requete supplémentaire
        # (obj.categories est caché via un prefetch_related)
        cats = obj.categories.all()
        return cats[0].value if cats else ""

    def get_category_display(self, obj):
        # On n'utilise volontairement pas .first() ici pour éviter une requete supplémentaire
        # (obj.categories est caché via un prefetch_related)
        cats = obj.categories.all()
        return cats[0].label if cats else ""

    def get_is_available(self, obj):
        return True

    def get_eligible_to_tally_form(self, obj):
        # Note : on ne peut pas se baser sur le `new_status` car les services
        # fraîchement publiés ne deviendront plus éligibles au formulaire Tally...
        return not obj.status_history_item.filter(
            previous_status=ServiceStatus.PUBLISHED
        ).exists()

    def get_forms_info(self, obj):
        forms = [{"name": form, "url": default_storage.url(form)} for form in obj.forms]
        return forms

    def get_diffusion_zone_type_display(self, obj):
        return _get_diffusion_zone_type_display(obj)

    def get_diffusion_zone_details_display(self, obj):
        return _get_diffusion_zone_details_display(obj)

    def get_access_conditions_display(self, obj):
        return [item.name for item in obj.access_conditions.all()]

    def get_concerned_public_display(self, obj):
        return [item.name for item in obj.concerned_public.all()]

    def get_requirements_display(self, obj):
        return [item.name for item in obj.requirements.all()]

    def get_credentials_display(self, obj):
        return [item.name for item in obj.credentials.all()]

    def get_department(self, obj):
        code = obj.city_code
        return code_insee_to_code_dept(code)

    def get_can_write(self, obj):
        user = self.context.get("request").user
        return obj.can_write(user)

    def validate(self, data):
        user = self.context.get("request").user
        structure = data.get("structure") or self.instance.structure

        user_structures = StructureMember.objects.filter(user_id=user.id).values_list(
            "structure_id", flat=True
        )

        if "structure" in data:
            if not user.is_staff and data["structure"].id not in user_structures:
                raise serializers.ValidationError(
                    {"structure": "Vous n’appartenez pas à cette structure"},
                    "not_member_of_struct",
                )

        assert structure.id is None or structure.id in user_structures or user.is_staff

        if "access_conditions" in data:
            self._validate_custom_choice(
                "access_conditions", data, user, user_structures, structure
            )

        if "concerned_public" in data:
            self._validate_custom_choice(
                "concerned_public", data, user, user_structures, structure
            )

        if "requirements" in data:
            self._validate_custom_choice(
                "requirements", data, user, user_structures, structure
            )

        if "credentials" in data:
            self._validate_custom_choice(
                "credentials", data, user, user_structures, structure
            )

        return data

    def _validate_custom_choice(self, field, data, user, user_structures, structure):
        values = data[field]
        for val in values:
            if val.structure_id is not None and val.structure_id != structure.id:
                raise serializers.ValidationError(
                    {field: "Ce choix n'est pas disponible dans cette structure"},
                    "unallowed_custom_choices_bad_struc",
                )

        return values

    def get_model_changed(self, object):
        if object.model:
            return object.model.sync_checksum != object.last_sync_checksum
        return None


class ServiceModelSerializer(ServiceSerializer):
    num_services = serializers.SerializerMethodField()
    access_conditions = ModelCreatablePrimaryKeyRelatedField(
        many=True,
        queryset=AccessCondition.objects.all(),
        max_length=140,
        required=False,
    )

    concerned_public = ModelCreatablePrimaryKeyRelatedField(
        many=True,
        queryset=ConcernedPublic.objects.all(),
        max_length=140,
        required=False,
    )
    requirements = ModelCreatablePrimaryKeyRelatedField(
        many=True,
        queryset=Requirement.objects.all(),
        max_length=140,
        required=False,
    )
    credentials = ModelCreatablePrimaryKeyRelatedField(
        many=True,
        queryset=Credential.objects.all(),
        max_length=140,
        required=False,
    )

    class Meta:
        model = ServiceModel

        fields = [
            "slug",
            "name",
            "short_desc",
            "full_desc",
            "kinds",
            "categories",
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
            "qpv_or_zrr",
            "recurrence",
            "structure",
            "creation_date",
            "modification_date",
            "suspension_date",
            "forms_info",
            "structure_info",
            "kinds_display",
            "categories_display",
            "subcategories_display",
            "access_conditions_display",
            "concerned_public_display",
            "requirements_display",
            "credentials_display",
            "beneficiaries_access_modes_display",
            "coach_orientation_modes_display",
            "department",
            "can_write",
            "num_services",
        ]
        lookup_field = "slug"

    def get_num_services(self, obj):
        return obj.copies.count()


class AnonymousServiceSerializer(ServiceSerializer):
    contact_name = serializers.SerializerMethodField()
    contact_phone = serializers.SerializerMethodField()
    contact_email = serializers.SerializerMethodField()
    is_contact_info_public = serializers.SerializerMethodField()

    def get_contact_name(self, obj):
        return obj.contact_name if obj.is_contact_info_public else ""

    def get_contact_phone(self, obj):
        return obj.contact_phone if obj.is_contact_info_public else ""

    def get_contact_email(self, obj):
        return obj.contact_email if obj.is_contact_info_public else ""

    def get_is_contact_info_public(self, obj):
        return True if obj.is_contact_info_public else None


class StructureSerializerInList(StructureSerializer):
    class Meta:
        model = Structure
        fields = [
            "slug",
            "name",
            "short_desc",
            "address1",
            "address2",
            "postal_code",
            "city",
            "url",
            "siret",
        ]


class ServiceListSerializer(ServiceSerializer):
    structure_info = StructureSerializerInList(source="structure", read_only=True)

    diffusion_zone_type_display = serializers.SerializerMethodField()
    diffusion_zone_details_display = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            "category",
            "category_display",
            "slug",
            "name",
            "structure",
            "structure_info",
            "postal_code",
            "city",
            "department",
            "status",
            "modification_date",
            "categories_display",
            "short_desc",
            "diffusion_zone_type",
            "diffusion_zone_type_display",
            "diffusion_zone_details_display",
            "model_changed",
            "model",
        ]
        lookup_field = "slug"

    def get_diffusion_zone_type_display(self, obj):
        return _get_diffusion_zone_type_display(obj)

    def get_diffusion_zone_details_display(self, obj):
        return _get_diffusion_zone_details_display(obj)


class FeedbackSerializer(serializers.Serializer):
    full_name = serializers.CharField()
    email = serializers.EmailField()
    message = serializers.CharField()
