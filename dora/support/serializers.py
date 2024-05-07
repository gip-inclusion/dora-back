from django.conf import settings
from rest_framework import serializers

from dora.core.models import LogItem, ModerationStatus
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

    # TdB
    categories = serializers.SerializerMethodField()
    has_admin = serializers.SerializerMethodField()
    num_services = serializers.SerializerMethodField()
    num_draft_services = serializers.SerializerMethodField()
    num_published_services = serializers.SerializerMethodField()
    num_outdated_services = serializers.SerializerMethodField()
    admins = serializers.SerializerMethodField()
    editors = serializers.SerializerMethodField()
    admins_to_moderate = serializers.SerializerMethodField()
    admins_to_remind = serializers.SerializerMethodField()
    num_potential_members_to_validate = serializers.SerializerMethodField()
    num_potential_members_to_remind = serializers.SerializerMethodField()

    class Meta:
        model = Structure
        fields = [
            "address1",
            "address2",
            "admins",
            "admins_to_moderate",
            "admins_to_remind",
            "ape",
            "branches",
            "categories",
            "city",
            "creation_date",
            "creator",
            "department",
            "editors",
            "email",
            "full_desc",
            "has_admin",
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
            "num_draft_services",
            "num_outdated_services",
            "num_potential_members_to_remind",
            "num_potential_members_to_validate",
            "num_published_services",
            "num_services",
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
        read_only_fields = [
            "address1",
            "address2",
            "admins",
            "admins_to_moderate",
            "admins_to_remind",
            "ape",
            "branches",
            "categories",
            "city",
            "creation_date",
            "creator",
            "department",
            "editors",
            "email",
            "full_desc",
            "has_admin",
            "last_editor",
            "latitude",
            "longitude",
            "members",
            "models",
            "moderation_date",
            "modification_date",
            "name",
            "notes",
            "num_draft_services",
            "num_outdated_services",
            "num_potential_members_to_remind",
            "num_potential_members_to_validate",
            "num_published_services",
            "num_services",
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

        return SMSerializer(obj.membership, many=True).data

    def get_pending_members(self, obj):
        class SPMSerializer(serializers.ModelSerializer):
            user = UserAdminSerializer()

            class Meta:
                model = StructurePutativeMember
                fields = ["user", "is_admin", "creation_date", "invited_by_admin"]

        return SPMSerializer(obj.putative_membership, many=True).data

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
        class BranchSerializer(serializers.ModelSerializer):
            class Meta:
                model = Structure
                fields = ["slug", "name", "short_desc"]
                lookup_field = "slug"

        return BranchSerializer(obj.branches.all(), many=True).data

    def get_models(self, obj):
        models = ServiceModel.objects.filter(structure=obj)

        class ModelSerializer(serializers.ModelSerializer):
            class Meta:
                model = ServiceModel
                fields = ["slug", "name", "short_desc"]
                lookup_field = "slug"

        return ModelSerializer(models, many=True).data

    def get_services(self, obj):
        class ServiceSerializer(serializers.ModelSerializer):
            class Meta:
                model = Service
                fields = ["slug", "name", "short_desc"]
                lookup_field = "slug"

        return ServiceSerializer(obj.services.published(), many=True).data

    def get_notes(self, obj):
        logs = LogItem.objects.filter(structure=obj).order_by("-date")
        return LogItemSerializer(logs, many=True).data

    def get_has_admin(self, obj):
        return obj.has_admin()

    def get_num_draft_services(self, obj):
        return obj.services.draft().count()

    def get_num_published_services(self, obj):
        return obj.services.published().count()

    def get_num_outdated_services(self, obj):
        return obj.services.update_advised().count()

    def get_num_services(self, obj):
        return obj.services.active().count()

    def get_categories(self, obj):
        return obj.services.values_list("categories__value", flat=True).distinct()

    def get_admins(self, obj):
        admins = obj.membership.filter(
            is_admin=True, user__is_valid=True, user__is_active=True
        )
        return [a.user.email for a in admins]

    def get_editors(self, obj):
        return set(
            s.last_editor.email
            for s in obj.services.published()
            if s.last_editor is not None
            and s.last_editor.email != settings.DORA_BOT_USER
        )

    def get_admins_to_moderate(self, obj):
        if obj.moderation_status != ModerationStatus.VALIDATED:
            return self.get_admins(obj)
        return []

    def get_admins_to_remind(self, obj):
        if not obj.has_admin():
            admins = obj.putative_membership.filter(
                is_admin=True,
                invited_by_admin=True,
                user__is_active=True,
            )
            return [a.user.email for a in admins]
        return []

    def get_num_potential_members_to_validate(self, obj):
        return obj.putative_membership.filter(
            invited_by_admin=False,
            user__is_valid=True,
            user__is_active=True,
        ).count()

    def get_num_potential_members_to_remind(self, obj):
        # les membres invités n'ont pas forcément validé leur adresse e-mail
        return obj.putative_membership.filter(
            invited_by_admin=True,
            user__is_active=True,
        ).count()


class StructureAdminListSerializer(StructureAdminSerializer):
    class Meta:
        model = Structure
        fields = [
            "admins",
            "admins_to_moderate",
            "admins_to_remind",
            "categories",
            "city",
            "department",
            "editors",
            "email",
            "has_admin",
            "is_obsolete",
            "latitude",
            "longitude",
            "moderation_date",
            "moderation_status",
            "name",
            "national_labels",
            "num_draft_services",
            "num_outdated_services",
            "num_potential_members_to_remind",
            "num_potential_members_to_validate",
            "num_published_services",
            "num_services",
            "phone",
            "short_desc",
            "siret",
            "slug",
            "typology",
            "typology_display",
        ]
        read_only_fields = [
            "admins",
            "admins_to_moderate",
            "admins_to_remind",
            "categories",
            "city",
            "department",
            "editors",
            "email",
            "has_admin",
            "is_obsolete",
            "latitude",
            "longitude",
            "moderation_date",
            "name",
            "national_labels",
            "num_draft_services",
            "num_outdated_services",
            "num_potential_members_to_remind",
            "num_potential_members_to_validate",
            "num_published_services",
            "num_services",
            "phone",
            "short_desc",
            "siret",
            "slug",
            "typology",
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
