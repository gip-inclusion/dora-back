from rest_framework import mixins, permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from dora.core.models import ModerationStatus
from dora.core.notify import send_moderation_notification
from dora.core.pagination import OptionalPageNumberPagination
from dora.core.utils import TRUTHY_VALUES
from dora.services.enums import ServiceStatus
from dora.services.models import Service
from dora.structures.emails import send_invitation_email
from dora.structures.models import Structure, StructurePutativeMember
from dora.support.serializers import (
    ServiceAdminListSerializer,
    ServiceAdminSerializer,
    StructureAdminListSerializer,
    StructureAdminSerializer,
)


class StructureAdminPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if request.method in [*permissions.SAFE_METHODS, "PATCH", "POST"]:
            return (
                user
                and user.is_authenticated
                and (user.is_staff or (user.is_manager and user.department))
            )
        return False


class ServiceAdminPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if request.method in [*permissions.SAFE_METHODS, "PATCH"]:
            return user and user.is_authenticated and user.is_staff
        return False


class ModerationMixin:
    def perform_update(self, serializer):
        status_before_update = serializer.instance.moderation_status
        status_after_update = (
            ModerationStatus(serializer.validated_data.get("moderation_status"))
            or status_before_update
        )

        if not status_before_update != status_after_update:
            raise serializers.ValidationError(
                "Mise à jour du statut de modération sans changement de statut"
            )
        msg = "Statut de modération changé par un•e membre de l'équipe"
        send_moderation_notification(
            serializer.instance, self.request.user, msg, status_after_update
        )


class StructureAdminViewSet(
    ModerationMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = StructureAdminSerializer
    permission_classes = [StructureAdminPermission]
    pagination_class = OptionalPageNumberPagination

    lookup_field = "slug"

    def get_queryset(self):
        user = self.request.user
        department = self.request.query_params.get("department")
        if user.is_manager and department and user.department != department:
            raise PermissionDenied
        if user.is_manager and not user.department:
            raise PermissionDenied
        if user.is_manager:
            department = user.department

        moderation = self.request.query_params.get("moderation") in TRUTHY_VALUES

        structures = Structure.objects.select_related("typology")
        if department:
            structures = structures.filter(department=department)
        if moderation:
            return structures.exclude(moderation_status=ModerationStatus.VALIDATED)
        return structures

    def get_serializer_class(self):
        if self.action == "list":
            return StructureAdminListSerializer
        return super().get_serializer_class()

    @action(
        detail=False,
        methods=["post"],
        url_path="resend-all-invite",
        permission_classes=[StructureAdminPermission],
    )
    # TODO: test permissions
    def resend_all_admin_invites(self, request):
        orphan_structures = Structure.objects.filter(
            department=request.user.department
        ).exclude(
            membership__is_admin=True,
            membership__user__is_valid=True,
            membership__user__is_active=True,
        )
        invited_admins = StructurePutativeMember.objects.filter(
            structure__in=orphan_structures, is_admin=True, invited_by_admin=True
        )
        actually_invited = []
        too_fresh = []
        for invited_admin in invited_admins:
            if send_invitation_email(
                invited_admin,
                request.user.get_full_name(),
            ):
                actually_invited.append(invited_admin.user.email)
            else:
                too_fresh.append((invited_admin.user.email))
        return Response({"reinvited": actually_invited, "blacklisted": too_fresh})


class ServiceAdminViewSet(
    ModerationMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ServiceAdminSerializer
    permission_classes = [ServiceAdminPermission]
    pagination_class = OptionalPageNumberPagination

    lookup_field = "slug"

    def get_queryset(self):
        moderation = self.request.query_params.get("moderation") in TRUTHY_VALUES
        all_services = Service.objects.select_related("structure").filter(
            status=ServiceStatus.PUBLISHED
        )
        if moderation:
            return all_services.exclude(moderation_status=ModerationStatus.VALIDATED)
        return all_services

    def get_serializer_class(self):
        if self.action == "list":
            return ServiceAdminListSerializer
        return super().get_serializer_class()
