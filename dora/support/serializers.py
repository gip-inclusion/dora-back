from rest_framework import serializers

from dora.core.models import LogItem
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
        read_only_fields = [
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


class LogItemSerializer(serializers.ModelSerializer):
    user = UserAdminSerializer()

    class Meta:
        fields = ["user", "message", "date"]
        model = LogItem


class StructureAdminSerializer(StructureSerializer):
    branches = serializers.SerializerMethodField()
    creator = UserAdminSerializer()
    last_editor = UserAdminSerializer()
    members = serializers.SerializerMethodField()
    models = serializers.SerializerMethodField()
    parent = serializers.SerializerMethodField()
    pending_members = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()
    notes = serializers.SerializerMethodField()

    class Meta:
        model = Structure
        fields = [
            "address1",
            "address2",
            "ape",
            "branches",
            "city",
            "creation_date",
            "creator",
            "department",
            "email",
            "full_desc",
            "last_editor",
            "latitude",
            "longitude",
            "members",
            "models",
            "moderation_status",
            "moderation_date",
            "modification_date",
            "name",
            "notes",
            "parent",
            "pending_members",
            "phone",
            "postal_code",
            "services",
            "short_desc",
            "siret",
            "slug",
            "source",
            "typology_display",
            "typology",
            "url",
        ]
        read_only_fields = [
            "address1",
            "address2",
            "ape",
            "branches",
            "city",
            "creation_date",
            "creator",
            "department",
            "email",
            "full_desc",
            "last_editor",
            "latitude",
            "longitude",
            "members",
            "models",
            "modification_date",
            "name",
            "notes",
            "parent",
            "pending_members",
            "phone",
            "postal_code",
            "services",
            "short_desc",
            "siret",
            "slug",
            "source",
            "typology_display",
            "typology",
            "url",
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
            }
        return {}

    def get_branches(self, obj):
        branches = obj.branches.all()

        class BranchSerializer(serializers.ModelSerializer):
            class Meta:
                model = Structure
                fields = ["slug", "name", "short_desc"]
                lookup_field = "slug"

        return BranchSerializer(branches, many=True).data

    def get_models(self, obj):
        models = ServiceModel.objects.filter(structure=obj)

        class ModelSerializer(serializers.ModelSerializer):
            class Meta:
                model = ServiceModel
                fields = ["slug", "name", "short_desc"]
                lookup_field = "slug"

        return ModelSerializer(models, many=True).data

    def get_services(self, obj):
        services = Service.objects.filter(structure=obj, status=ServiceStatus.PUBLISHED)

        class ServiceSerializer(serializers.ModelSerializer):
            class Meta:
                model = Service
                fields = ["slug", "name", "short_desc"]
                lookup_field = "slug"

        return ServiceSerializer(services, many=True).data

    def get_notes(self, obj):
        logs = LogItem.objects.filter(structure=obj).order_by("-date")
        return LogItemSerializer(logs, many=True).data


class StructureAdminListSerializer(StructureAdminSerializer):
    class Meta:
        model = Structure
        fields = [
            "slug",
            "name",
            "department",
            "moderation_status",
            "moderation_date",
            "typology_display",
        ]
        read_only_fields = [
            "slug",
            "name",
            "department",
            "typology_display",
        ]
        lookup_field = "slug"


class ServiceAdminSerializer(ServiceSerializer):
    creator = UserAdminSerializer()
    last_editor = UserAdminSerializer()
    model = serializers.SerializerMethodField()
    structure = StructureAdminSerializer()
    notes = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            "categories_display",
            "city",
            "contact_email",
            "contact_name",
            "contact_phone",
            "creation_date",
            "creator",
            "department",
            "diffusion_zone_details_display",
            "diffusion_zone_type_display",
            "fee_details",
            "full_desc",
            "fee_condition",
            "is_contact_info_public",
            "last_editor",
            "model",
            "moderation_status",
            "moderation_date",
            "modification_date",
            "name",
            "notes",
            "postal_code",
            "short_desc",
            "slug",
            "structure",
            "subcategories_display",
        ]
        read_only_fields = [
            "categories_display",
            "city",
            "contact_email",
            "contact_name",
            "contact_phone",
            "creation_date",
            "creator",
            "department",
            "diffusion_zone_details_display",
            "diffusion_zone_type_display",
            "fee_details",
            "full_desc",
            "fee_condition",
            "is_contact_info_public",
            "last_editor",
            "model",
            "modification_date",
            "name",
            "notes",
            "postal_code",
            "short_desc",
            "slug",
            "structure",
            "subcategories_display",
        ]
        lookup_field = "slug"

    def get_model(self, obj):
        if obj.model:
            return {"name": obj.model.name, "slug": obj.model.slug}
        return {}

    def get_notes(self, obj):
        logs = LogItem.objects.filter(service=obj).order_by("-date")
        return LogItemSerializer(logs, many=True).data


class ServiceAdminListSerializer(ServiceAdminSerializer):
    structure_name = serializers.SerializerMethodField()
    structure_dept = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            "name",
            "slug",
            "diffusion_zone_type",
            "diffusion_zone_type_display",
            "diffusion_zone_details_display",
            "moderation_status",
            "moderation_date",
            "structure_name",
            "structure_dept",
        ]
        read_only_fields = [
            "name",
            "slug",
            "diffusion_zone_type",
            "diffusion_zone_type_display",
            "diffusion_zone_details_display",
            "structure_name",
            "structure_dept",
        ]

    def get_structure_name(self, obj):
        return obj.structure.name

    def get_structure_dept(self, obj):
        return obj.structure.department
