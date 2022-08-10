from rest_framework import serializers

from dora.services.enums import ServiceStatus
from dora.services.models import Service, ServiceModel
from dora.services.serializers import ServiceSerializer
from dora.structures.models import Structure, StructureMember, StructurePutativeMember
from dora.structures.serializers import StructureSerializer
from dora.users.models import User


class UserAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "email",
            "is_active",
            "is_valid",
            "date_joined",
            "newsletter",
        ]


class StructureAdminSerializer(StructureSerializer):
    creator = UserAdminSerializer()
    last_editor = UserAdminSerializer()
    source = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    pending_members = serializers.SerializerMethodField()
    parent = serializers.SerializerMethodField()
    branches = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()
    models = serializers.SerializerMethodField()

    class Meta:
        model = Structure
        fields = [
            "siret",
            "typology",
            "typology_display",
            "slug",
            "name",
            "short_desc",
            "url",
            "full_desc",
            "phone",
            "email",
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
            "parent",
            "branches",
            "has_admin",
            "num_services",
            "services",
            "archived_services",
            "num_models",
            "models",
            "creator",
            "last_editor",
            "source",
            "members",
            "pending_members",
        ]
        lookup_field = "slug"

    def get_members(self, obj):
        class SMSerializer(serializers.ModelSerializer):
            user = UserAdminSerializer()

            class Meta:
                model = StructureMember
                fields = ["user", "is_admin", "creation_date"]

        members = StructureMember.objects.filter(structure=obj)
        return SMSerializer(members, many=True).data

    def get_pending_members(self, obj):
        class SPMSerializer(serializers.ModelSerializer):
            user = UserAdminSerializer()

            class Meta:
                model = StructurePutativeMember
                fields = ["user", "is_admin", "creation_date", "invited_by_admin"]

        pmembers = StructurePutativeMember.objects.filter(structure=obj)
        return SPMSerializer(pmembers, many=True).data

    def get_source(self, obj):
        return obj.source.label if obj.source else ""

    def get_parent(self, obj):
        if obj.parent:
            return {
                "name": obj.parent.name,
                "slug": obj.parent.slug,
                "id": obj.parent.pk,
            }
        return {}

    def get_branches(self, obj):
        branches = obj.branches.all()

        class BranchSerializer(serializers.ModelSerializer):
            class Meta:
                model = Structure
                fields = ["slug", "name", "id", "short_desc"]
                lookup_field = "slug"

        return BranchSerializer(branches, many=True).data

    def get_models(self, obj):
        models = ServiceModel.objects.filter(structure=obj)

        class ModelSerializer(serializers.ModelSerializer):
            class Meta:
                model = ServiceModel
                fields = ["slug", "name", "id", "short_desc"]
                lookup_field = "slug"

        return ModelSerializer(models, many=True).data

    def get_services(self, obj):
        services = Service.objects.filter(structure=obj, status=ServiceStatus.PUBLISHED)

        class ServiceSerializer(serializers.ModelSerializer):
            class Meta:
                model = Service
                fields = ["slug", "name", "id", "short_desc"]
                lookup_field = "slug"

        return ServiceSerializer(services, many=True).data


class StructureAdminListSerializer(StructureAdminSerializer):
    class Meta:
        model = Structure
        fields = [
            "slug",
            "name",
            "department",
            "typology_display",
        ]
        lookup_field = "slug"


# class StructureModerationSerializer(serializers.ModelSerializer):
#     creator = UserModerationSerializer()
#     last_editor = UserModerationSerializer()
#     members = serializers.SerializerMethodField()

#     class Meta:
#         model = Structure
#         fields = [
#             "slug",
#             "name",
#             "creator",
#             "last_editor",
#             "members",
#             "url",
#             "phone",
#             "email",
#         ]

#     def get_members(self, obj):
#         class SMSerializer(serializers.ModelSerializer):
#             user = UserModerationSerializer()

#             class Meta:
#                 model = StructureMember
#                 fields = ["user", "creation_date", "is_admin"]

#         members = StructureMember.objects.filter(structure=obj)
#         return SMSerializer(members, many=True).data


class ServiceAdminSerializer(ServiceSerializer):

    creator = UserAdminSerializer()
    last_editor = UserAdminSerializer()
    structure = StructureAdminSerializer()
    model = serializers.SerializerMethodField()

    class Meta:
        model = Service
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
            "model",
            "creator",
            "last_editor",
        ]
        lookup_field = "slug"

    def get_model(self, obj):
        if obj.model:
            return {"name": obj.model.name, "slug": obj.model.slug}
        return {}


class ServiceAdminListSerializer(ServiceAdminSerializer):
    structure_name = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            "name",
            "slug",
            "diffusion_zone_type",
            "diffusion_zone_type_display",
            "diffusion_zone_details_display",
            "structure_name",
        ]

    def get_structure_name(self, obj):
        return obj.structure.name
