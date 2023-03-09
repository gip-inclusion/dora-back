from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework import mixins, permissions, serializers, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from dora.core.models import ModerationStatus
from dora.core.notify import send_moderation_notification
from dora.core.pagination import OptionalPageNumberPagination
from dora.core.utils import TRUTHY_VALUES
from dora.services.enums import ServiceStatus
from dora.services.models import Service
from dora.structures.models import Structure, StructureMember
from dora.support.serializers import (
    ServiceAdminListSerializer,
    ServiceAdminSerializer,
    StructureAdminListSerializer,
    StructureAdminSerializer,
)
from dora.users.models import User


class StructureAdminPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if request.method in [*permissions.SAFE_METHODS, "PATCH"]:
            return (
                user
                and user.is_authenticated
                and (user.is_staff or (user.is_local_coordinator and user.department))
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
        if user.is_local_coordinator and department and user.department != department:
            raise PermissionDenied
        if user.is_local_coordinator and not user.department:
            raise PermissionDenied
        if user.is_local_coordinator:
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


def get_num_users(dept):
    all_users = User.objects.filter(is_valid=True, is_active=True)
    if dept:
        all_users = all_users.filter(membership__structure__department=dept)
    return all_users.distinct().count()


def get_num_published_services(dept):
    all_services = Service.objects.published()
    if dept:
        all_services = all_services.filter(structure__department=dept)
    return all_services.distinct().count()


def get_num_orphan_structs(dept):
    administrators = StructureMember.objects.filter(
        is_admin=True, user__is_active=True, user__is_valid=True
    )
    all_structs = Structure.objects.exclude(
        membership__in=administrators,
    )
    if dept:
        all_structs = all_structs.filter(department=dept)
    return all_structs.distinct().count()


def get_num_active_structs(dept):
    # nombre de structures
    # - ayant au moins 1 service publié et actif (n'ayant pas dépassé la date de disponibilité)
    # ou
    # - ayant un utilisateur s'étant connecté dans les 30 derniers jours

    visible_services = Service.objects.published().filter(
        Q(suspension_date__gt=timezone.now()) | Q(suspension_date=None)
    )
    active_users = User.objects.filter(
        is_active=True,
        is_valid=True,
        last_login__gt=timezone.now() - timedelta(days=30),
    )

    structures = Structure.objects.filter(
        Q(membership__user__in=active_users) | Q(services__in=visible_services)
    ).distinct()

    if dept:
        structures = structures.filter(department=dept)
    return structures.count()


@api_view()
@permission_classes([StructureAdminPermission])
def stats(request):
    user = request.user
    department = request.query_params.get("department")
    if user.is_local_coordinator and department and user.department != department:
        raise PermissionDenied
    if user.is_local_coordinator and not user.department:
        raise PermissionDenied
    if user.is_local_coordinator:
        department = user.department

    return Response(
        {
            "nb_active_structs": get_num_active_structs(department),
            "nb_orphan_structs": get_num_orphan_structs(department),
            "nb_published_services": get_num_published_services(department),
            "nb_users": get_num_users(department),
        }
    )
