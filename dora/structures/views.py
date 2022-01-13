from datetime import timedelta

from django.conf import settings
from django.db.models.query_utils import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import exceptions, mixins, permissions, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from dora.core.notify import send_mattermost_notification
from dora.rest_auth.models import Token
from dora.structures.emails import send_invitation_email
from dora.structures.models import (
    Structure,
    StructureMember,
    StructurePutativeMember,
    StructureSource,
    StructureTypology,
)
from dora.structures.permissions import (
    StructureMemberPermission,
    StructurePermission,
    StructurePutativeMemberPermission,
)

from .serializers import (
    SiretClaimedSerializer,
    StructureListSerializer,
    StructureMemberSerializer,
    StructurePutativeMemberSerializer,
    StructureSerializer,
)


class StructureViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = StructureSerializer
    permission_classes = [StructurePermission]
    lookup_field = "slug"

    def get_my_structures(self, user):
        if not user or not user.is_authenticated:
            return Structure.objects.none()
        return Structure.objects.filter(membership__user=user)

    def get_my_pending_structures(self, user):
        if not user or not user.is_authenticated:
            return Structure.objects.none()
        return Structure.objects.filter(putative_membership__user=user)

    def get_queryset(self):
        user = self.request.user
        only_mine = self.request.query_params.get("mine")
        only_pending = self.request.query_params.get("pending")

        if only_mine:
            return (
                self.get_my_structures(user).order_by("-modification_date").distinct()
            )
        elif only_pending:
            return (
                self.get_my_pending_structures(user)
                .order_by("-modification_date")
                .distinct()
            )
        else:
            return Structure.objects.all().order_by("-modification_date")

    def get_serializer_class(self):
        if self.action == "list":
            return StructureListSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        user = self.request.user
        source = (
            StructureSource.DORA_STAFF
            if user.is_staff
            else StructureSource.STRUCT_STAFF
        )
        structure = serializer.save(creator=user, last_editor=user, source=source)
        send_mattermost_notification(
            f":office: Nouvelle structure “{structure.name}” créée dans le departement : **{structure.department}**\n{settings.FRONTEND_URL}/structures/{structure.slug}"
        )
        # When creating a structure, the creator becomes member and administrator of this structure
        StructureMember.objects.create(user=user, structure=structure, is_admin=True)

    def perform_update(self, serializer):
        serializer.save(last_editor=self.request.user)


class StructureMemberViewset(viewsets.ModelViewSet):
    serializer_class = StructureMemberSerializer
    permission_classes = [StructureMemberPermission]

    def get_queryset(self):

        structure_slug = self.request.query_params.get("structure")
        user = self.request.user

        if self.action in ("list"):
            if structure_slug is None:
                return StructureMember.objects.none()

            if user.is_staff:
                return StructureMember.objects.filter(structure__slug=structure_slug)

            try:
                StructureMember.objects.get(
                    user_id=user.id, is_admin=True, structure__slug=structure_slug
                )
            except StructureMember.DoesNotExist:
                raise exceptions.PermissionDenied

            return StructureMember.objects.filter(structure__slug=structure_slug)
        else:
            if user.is_staff:
                return StructureMember.objects.all()

            structures_administered = StructureMember.objects.filter(
                user_id=user.id, is_admin=True
            ).values_list("structure_id", flat=True)
            return StructureMember.objects.filter(
                structure_id__in=structures_administered
            )


class StructurePutativeMemberViewset(viewsets.ModelViewSet):
    serializer_class = StructurePutativeMemberSerializer
    permission_classes = [StructurePutativeMemberPermission]

    def get_queryset(self):

        structure_slug = self.request.query_params.get("structure")
        user = self.request.user

        # TODO: simplify
        if self.action in ("list", "create"):
            if structure_slug is None:
                return StructurePutativeMember.objects.none()

            if user.is_staff:
                return StructurePutativeMember.objects.filter(
                    structure__slug=structure_slug
                )

            try:
                # Ensure requester is structure admin
                StructureMember.objects.get(
                    user_id=user.id, is_admin=True, structure__slug=structure_slug
                )
            except StructureMember.DoesNotExist:
                raise exceptions.PermissionDenied

            return StructurePutativeMember.objects.filter(
                Q(user__is_valid=True) | Q(invited_by_admin=True),
                structure__slug=structure_slug,
            )
        else:
            if user.is_staff:
                return StructurePutativeMember.objects.all()

            structures_administered = StructureMember.objects.filter(
                user_id=user.id, is_admin=True
            ).values_list("structure_id", flat=True)
            return StructurePutativeMember.objects.filter(
                structure_id__in=structures_administered
            )

    @action(
        detail=True,
        methods=["post"],
        url_path="accept-invite",
        permission_classes=[permissions.IsAuthenticated],
    )
    def accept_invite(self, request, pk):
        try:
            pm = StructurePutativeMember.objects.get(id=pk)
        except StructurePutativeMember.DoesNotExist:
            raise exceptions.NotFound

        user = request.user

        if pm.user.id != user.id:
            raise exceptions.PermissionDenied

        structure_name = pm.structure.name

        if not user.is_valid:
            user.is_valid = True
            user.save()

        must_set_password = not user.has_usable_password()
        if must_set_password:
            # generate a new short term token for password reset
            # The invitation token will be deleted as soon as the user sets a password
            tmp_token = Token.objects.create(
                user=user, expiration=timezone.now() + timedelta(minutes=30)
            )
        else:
            membership = StructureMember.objects.create(
                user=pm.user,
                structure=pm.structure,
                is_admin=pm.will_be_admin,
            )
            # TODO: atomic
            pm.delete()
            # The user already exists and hopefully know its password
            # we can safely delete the invitation token
            Token.objects.filter(user=user, expiration__isnull=False).delete()

            # Then notify the administrators of this structure
            membership.notify_admins_invitation_accepted()
        return Response(
            {
                "structure_name": structure_name,
                "must_set_password": must_set_password,
                "token": tmp_token.key if must_set_password else None,
            },
            status=200,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="resend-invite",
        permission_classes=[permissions.IsAuthenticated],
    )
    def resend_invite(self, request, pk):
        try:
            member = StructurePutativeMember.objects.get(id=pk)
        except StructurePutativeMember.DoesNotExist:
            raise exceptions.NotFound
        # Ensure the requester is admin of the structure, or superuser
        structure = member.structure
        request_user = request.user
        if not request_user.is_staff:
            try:
                StructureMember.objects.get(
                    user_id=request_user.id, is_admin=True, structure_id=structure.id
                )
            except StructureMember.DoesNotExist:
                raise exceptions.PermissionDenied

        # TODO: ensure we work on putative members and not members
        # Can't reinvite a valid user
        # if member.has_accepted_invitation and member.user.has_usable_password():
        #     raise exceptions.PermissionDenied

        tmp_token = Token.objects.create(
            user=member.user, expiration=timezone.now() + timedelta(days=7)
        )
        send_invitation_email(
            member,
            request_user.get_full_name(),
            tmp_token.key,
        )
        return Response(status=201)

    @action(
        detail=True,
        methods=["post"],
        url_path="accept",
        permission_classes=[permissions.IsAuthenticated],
    )
    def accept(self, request, pk):
        # TODO: check permissions
        # TODO: add tests
        # TODO: ensure the user has a valid email address
        # TODO: ensure the user is active
        try:
            pm = StructurePutativeMember.objects.get(id=pk)
        except StructurePutativeMember.DoesNotExist:
            raise exceptions.NotFound
        # Ensure the requester is admin of the structure, or superuser
        structure = pm.structure
        request_user = request.user
        if not request_user.is_staff:
            try:
                StructureMember.objects.get(
                    user_id=request_user.id, is_admin=True, structure_id=structure.id
                )
            except StructureMember.DoesNotExist:
                raise exceptions.PermissionDenied

        # TODO: atomic
        # TODO: ensure that the user is valid
        membership = StructureMember.objects.create(
            user=pm.user,
            structure=pm.structure,
            is_admin=pm.will_be_admin,
        )
        pm.delete()
        membership.notify_access_granted()

        return Response(status=201)


@api_view()
@permission_classes([permissions.AllowAny])
def siret_was_claimed(request, siret):
    structure = get_object_or_404(Structure.objects.all(), siret=siret)
    serializer = SiretClaimedSerializer(structure, context={"request": request})
    return Response(serializer.data)


@api_view()
@permission_classes([permissions.AllowAny])
def options(request):

    result = {
        "typologies": [
            {"value": c[0], "label": c[1]} for c in StructureTypology.choices
        ],
    }
    return Response(result)


@api_view()
@permission_classes([permissions.AllowAny])
def search_safir(request):
    safir_code = request.query_params.get("safir", "")
    if not safir_code:
        return Response("need safir")

    structure = get_object_or_404(Structure, code_safir_pe=safir_code)
    return Response(StructureSerializer(structure, context={"request": request}).data)
