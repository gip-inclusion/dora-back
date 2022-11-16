import logging

from django.conf import settings
from django.db import transaction
from django.http.response import Http404
from django.utils import timezone
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework import exceptions, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from dora.core.models import ModerationStatus
from dora.core.notify import send_mattermost_notification, send_moderation_notification
from dora.rest_auth.authentication import TokenAuthentication
from dora.structures.models import (
    Structure,
    StructureMember,
    StructurePutativeMember,
    StructureSource,
)
from dora.structures.serializers import StructureSerializer

from .serializers import JoinStructureSerializer, TokenSerializer, UserInfoSerializer

logger = logging.getLogger(__name__)


def update_last_login(user):
    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])


@sensitive_post_parameters(["key"])
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def user_info(request):
    serializer = TokenSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    key = serializer.validated_data["key"]
    try:
        user, _token = TokenAuthentication().authenticate_credentials(key)
    except exceptions.AuthenticationFailed:
        raise Http404
    update_last_login(user)
    return Response(UserInfoSerializer(user).data, status=200)


def _create_structure(establishment, user):
    try:
        structure = Structure.objects.get(siret=establishment.siret)
    except Structure.DoesNotExist:
        structure = Structure.objects.create_from_establishment(establishment)
        structure.creator = user
        structure.last_editor = user
        structure.source = StructureSource.objects.get(value="porteur")
        structure.save()
        send_moderation_notification(
            structure,
            user,
            "Structure créée lors d'une inscription",
            ModerationStatus.VALIDATED,
        )
        send_mattermost_notification(
            f":office: Nouvelle structure “{structure.name}” créée dans le departement : **{structure.department}**\n{structure.get_absolute_url()}"
        )

    return structure


def _is_member_of_structure(structure, user):
    try:
        StructureMember.objects.get(user=user, structure=structure)
        return True
    except StructureMember.DoesNotExist:
        return False


def _add_user_to_adminless_structure(structure, user):
    add_as_admin = True
    # Si l'utilisateur a été invité (a priori par un superuser), on supprime l'invitation
    try:
        pm = StructurePutativeMember.objects.get(
            user=user,
            structure=structure,
        )
        add_as_admin = pm.is_admin
        pm.delete()
    except StructurePutativeMember.DoesNotExist:
        pass

    # Puis on l'ajoute comme collaborateur
    # (admin par defaut, sauf s'il a été invité comme utilisateur normal)
    StructureMember.objects.create(
        user=user, structure=structure, is_admin=add_as_admin
    )
    send_moderation_notification(
        structure,
        user,
        "Premier administrateur ajouté (par lui-même)",
        ModerationStatus.NEED_INITIAL_MODERATION,
    )
    send_mattermost_notification(
        f":adult: Premier administrateur “{user.get_full_name()}” enregistré dans la structure : **{structure.name} ({structure.department})**\n{settings.FRONTEND_URL}/structures/{structure.slug}"
    )


def _add_user_to_structure_or_waitlist(structure, user):
    # Si l'utilisateur a été invité, on le valide directement
    try:
        pm = StructurePutativeMember.objects.get(
            user=user,
            structure=structure,
            invited_by_admin=True,
        )

        membership = StructureMember.objects.create(
            user=pm.user,
            structure=pm.structure,
            is_admin=pm.is_admin,
        )
        pm.delete()
        membership.notify_admins_invitation_accepted()
    except StructurePutativeMember.DoesNotExist:
        # Sinon on le met en liste d'attente, ou on re-notifie l'administrateur s'il y était déjà
        pm, _created = StructurePutativeMember.objects.get_or_create(
            user=user,
            structure=structure,
            is_admin=False,
            defaults={"invited_by_admin": False},
        )
        pm.notify_admin_access_requested()


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@transaction.atomic
def join_structure(request):
    user = request.user
    serializer = JoinStructureSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    establishment = data.get("establishment")

    if establishment:
        structure = _create_structure(establishment, user)
    else:
        structure = data.get("structure")

    structure_has_admin = structure.membership.filter(
        user__is_valid=True, user__is_active=True, is_admin=True
    ).exists()

    if _is_member_of_structure(structure, user):
        return Response(
            StructureSerializer(structure, context={"request": request}).data
        )

    was_already_member_of_a_structure = StructureMember.objects.filter(
        user=user, structure=structure
    ).exists()

    if not structure_has_admin:
        _add_user_to_adminless_structure(structure, user)
    else:
        _add_user_to_structure_or_waitlist(structure, user)

    if not was_already_member_of_a_structure:
        user.start_onboarding()

    return Response(StructureSerializer(structure, context={"request": request}).data)
