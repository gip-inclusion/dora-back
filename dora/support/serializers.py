from rest_framework import serializers

from dora.core.models import LogItem
from dora.services.enums import ServiceStatus
from dora.services.models import Service, ServiceModel
from dora.services.serializers import ServiceSerializer
from dora.structures.models import Structure, StructureMember, StructurePutativeMember
from dora.structures.serializers import StructureSerializer
from dora.users.models import User


class UserAdminSerializer(serializers.ModelSerializer):
    is_on_ic = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "date_joined",
            "email",
            "email",
            "first_name",
            "is_active",
            "is_on_ic",
            "is_valid",
            "last_name",
            "newsletter",
            "phone_number",
        ]
        read_only_fields = [
            "date_joined",
            "email",
            "email",
            "first_name",
            "is_active",
            "is_valid",
            "last_name",
            "newsletter",
            "phone_number",
        ]

    def get_is_on_ic(self, obj):
        return obj.ic_id is not None


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
    categories = serializers.SerializerMethodField()

    has_admin = serializers.SerializerMethodField()
    has_putative_admin = serializers.SerializerMethodField()
    has_active_users = serializers.SerializerMethodField()
    num_services = serializers.SerializerMethodField()
    num_outdated_services = serializers.SerializerMethodField()

    class Meta:
        model = Structure
        fields = [
            "address1",
            "address2",
            "ape",
            "branches",
            "categories",
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
            "moderation_date",
            "moderation_status",
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
            "typology",
            "typology_display",
            "url",
            "has_admin",
            "has_putative_admin",
            "has_active_users",
            "num_services",
            "num_outdated_services",
        ]
        read_only_fields = [
            "address1",
            "address2",
            "ape",
            "branches",
            "categories",
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
            "typology",
            "typology_display",
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

    def get_has_admin(self, obj):
        return StructureMember.objects.filter(
            user__is_active=True, user__is_valid=True, structure=obj, is_admin=True
        ).exists()

    def get_has_putative_admin(self, obj):
        return False

    def get_has_active_users(self, obj):
        return False

    def get_num_services(self, obj):
        return Service.objects.published().filter(structure=obj).count()

    def get_num_outdated_services(self, obj):
        return (
            Service.objects.update_mandatory()
            .filter(
                structure=obj,
            )
            .count()
        )

    def get_categories(self, obj):
        return obj.services.values_list("categories__value", flat=True).distinct()


class StructureAdminListSerializer(StructureAdminSerializer):
    class Meta:
        model = Structure
        fields = [
            "categories",
            "department",
            "latitude",
            "longitude",
            "moderation_date",
            "moderation_status",
            "name",
            "slug",
            "typology",
            "typology_display",
            "has_admin",
            "has_putative_admin",
            "has_active_users",
            "moderation_date",
            "moderation_status",
            "num_services",
            "num_outdated_services",
            "short_desc",
        ]
        read_only_fields = [
            "categories",
            "department",
            "name",
            "slug",
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
            "fee_condition",
            "fee_details",
            "full_desc",
            "is_contact_info_public",
            "last_editor",
            "model",
            "moderation_date",
            "moderation_status",
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
            "fee_condition",
            "fee_details",
            "full_desc",
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
            "diffusion_zone_details_display",
            "diffusion_zone_type",
            "diffusion_zone_type_display",
            "moderation_date",
            "moderation_status",
            "name",
            "slug",
            "structure_dept",
            "structure_name",
        ]
        read_only_fields = [
            "diffusion_zone_details_display",
            "diffusion_zone_type",
            "diffusion_zone_type_display",
            "name",
            "slug",
            "structure_dept",
            "structure_name",
        ]

    def get_structure_name(self, obj):
        return obj.structure.name

    def get_structure_dept(self, obj):
        return obj.structure.department
