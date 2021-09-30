import logging

from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from rest_framework import serializers
from rest_framework.relations import PrimaryKeyRelatedField

from dora.structures.models import Structure, StructureMember

from .models import (
    AccessCondition,
    BeneficiaryAccessMode,
    CoachOrientationMode,
    ConcernedPublic,
    Credential,
    LocationKind,
    Requirement,
    Service,
    ServiceCategories,
    ServiceKind,
    ServiceSubCategories,
)

logger = logging.getLogger(__name__)


class CreatablePrimaryKeyRelatedField(PrimaryKeyRelatedField):
    def use_pk_only_optimization(self):
        return True

    def to_internal_value(self, data):
        if isinstance(data, int):
            return super().to_internal_value(data)

        # If we receive a string instead of a primary key, search
        # by value, and create a new object if not found
        if self.root.instance:
            structure = self.root.instance.structure
        else:
            structure_slug = self.root.initial_data["structure"]
            structure = Structure.objects.get(slug=structure_slug)
        if not structure:
            raise ValidationError("La structure ne peut pas être vide")
        queryset = self.queryset

        # find if it already exists in the same structure
        obj = queryset.filter(name=data, structure=structure).first()
        if not obj:
            # then in the global repository
            obj = queryset.filter(name=data, structure=None).first()
        if not obj:
            # otherwise create it
            obj = queryset.create(name=data, structure=structure)
        return obj


class StructureSerializer(serializers.ModelSerializer):
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
        ]


class ServiceSerializer(serializers.ModelSerializer):
    is_available = serializers.SerializerMethodField()
    forms_info = serializers.SerializerMethodField()
    structure = serializers.SlugRelatedField(
        queryset=Structure.objects.all(), slug_field="slug"
    )
    structure_info = StructureSerializer(source="structure", read_only=True)
    kinds_display = serializers.SerializerMethodField()
    category_display = serializers.SerializerMethodField()
    subcategories_display = serializers.SerializerMethodField()
    access_conditions = CreatablePrimaryKeyRelatedField(
        many=True,
        queryset=AccessCondition.objects.all(),
        required=False,
    )
    access_conditions_display = serializers.SerializerMethodField()
    concerned_public = CreatablePrimaryKeyRelatedField(
        many=True,
        queryset=ConcernedPublic.objects.all(),
        required=False,
    )
    concerned_public_display = serializers.SerializerMethodField()
    requirements = CreatablePrimaryKeyRelatedField(
        many=True,
        queryset=Requirement.objects.all(),
        required=False,
    )
    requirements_display = serializers.SerializerMethodField()
    credentials = CreatablePrimaryKeyRelatedField(
        many=True,
        queryset=Credential.objects.all(),
        required=False,
    )
    credentials_display = serializers.SerializerMethodField()
    location_kinds_display = serializers.SerializerMethodField()
    beneficiaries_access_modes_display = serializers.SerializerMethodField()
    coach_orientation_modes_display = serializers.SerializerMethodField()
    recurrence_display = serializers.CharField(
        source="get_recurrence_display", read_only=True
    )
    department = serializers.SerializerMethodField()
    can_write = serializers.SerializerMethodField()

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
            "is_common_law",
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
            "remote_url",
            "address1",
            "address2",
            "postal_code",
            "city_code",
            "city",
            "geom",
            "start_date",
            "end_date",
            "recurrence",
            "recurrence_other",
            "suspension_count",
            "suspension_date",
            "structure",
            "creation_date",
            "modification_date",
            "is_draft",
            "is_available",
            "forms_info",
            "structure",
            "structure_info",
            "kinds_display",
            "category_display",
            "subcategories_display",
            "access_conditions_display",
            "concerned_public_display",
            "requirements_display",
            "credentials_display",
            "location_kinds_display",
            "beneficiaries_access_modes_display",
            "coach_orientation_modes_display",
            "recurrence_display",
            "department",
            "can_write",
        ]
        lookup_field = "slug"

    def get_is_available(self, obj):
        return True

    def get_forms_info(self, obj):
        forms = [{"name": form, "url": default_storage.url(form)} for form in obj.forms]
        return forms

    def get_kinds_display(self, obj):
        return [ServiceKind(kind).label for kind in obj.kinds]

    def get_location_kinds_display(self, obj):
        return [LocationKind(kind).label for kind in obj.location_kinds]

    def get_category_display(self, obj):
        return ServiceCategories(obj.category).label if obj.category else ""

    def get_subcategories_display(self, obj):
        try:
            return [ServiceSubCategories(cat).label for cat in obj.subcategories]
        except ValueError:
            logger.exception(
                "Incorrect Service sub-category", extra={"values": obj.subcategories}
            )
            return []

    def get_beneficiaries_access_modes_display(self, obj):
        return [
            BeneficiaryAccessMode(mode).label for mode in obj.beneficiaries_access_modes
        ]

    def get_coach_orientation_modes_display(self, obj):
        return [
            CoachOrientationMode(mode).label for mode in obj.coach_orientation_modes
        ]

    def get_access_conditions_display(self, obj):
        return [item.name for item in obj.access_conditions.all()]

    def get_concerned_public_display(self, obj):
        return [item.name for item in obj.concerned_public.all()]

    def get_requirements_display(self, obj):
        return [item.name for item in obj.requirements.all()]

    def get_credentials_display(self, obj):
        return [item.name for item in obj.credentials.all()]

    def get_department(self, obj):
        return obj.postal_code[0:2]

    def get_can_write(self, obj):
        user = self.context.get("request").user
        return obj.can_write(user)

    # def validate_structure(self, value):
    #     user = self.context.get("request").user

    #     if (
    #         not user.is_staff
    #         and not StructureMember.objects.filter(
    #             structure_id=value.id, user_id=user.id
    #         ).exists()
    #     ):
    #         raise serializers.ValidationError(
    #             "Vous n’appartenez pas à cette structure", "not_member_of_struct"
    #         )

    #     return value

    def validate(self, data):
        user = self.context.get("request").user
        user_structures = StructureMember.objects.filter(user_id=user.id).values_list(
            "structure_id", flat=True
        )

        if "structure" in data:
            if not user.is_staff and data["structure"].id not in user_structures:
                raise serializers.ValidationError(
                    {"structure": "Vous n’appartenez pas à cette structure"},
                    "not_member_of_struct",
                )
        return data

    def _validate_custom_choice(self, values):
        user = self.context.get("request").user
        if user.is_staff:
            return values
        user_structures = StructureMember.objects.filter(user_id=user.id).values_list(
            "structure_id", flat=True
        )
        for val in values:
            if val.structure_id is not None and val.structure_id not in user_structures:
                raise serializers.ValidationError(
                    "Ce choix n'est pas disponible dans cette structure",
                    "unallowed_custom_choices",
                )
        return values

    def validate_access_conditions(self, value):
        return self._validate_custom_choice(value)

    def validate_concerned_public(self, value):
        return self._validate_custom_choice(value)

    def validate_requirements(self, value):
        return self._validate_custom_choice(value)

    def validate_credentials(self, value):
        return self._validate_custom_choice(value)


class ServiceListSerializer(ServiceSerializer):
    class Meta:
        model = Service
        fields = [
            "slug",
            "name",
            "structure_info",
            "department",
            "is_draft",
            "modification_date",
        ]
        lookup_field = "slug"
