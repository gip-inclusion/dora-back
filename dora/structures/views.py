from django.conf import settings
from django.db import transaction
from django.db.models.query_utils import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import exceptions, mixins, permissions, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from dora.core.notify import send_mattermost_notification, send_moderation_email
from dora.core.pagination import OptionalPageNumberPagination
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
    pagination_class = OptionalPageNumberPagination

    lookup_field = "slug"

    def get_queryset(self):
        user = self.request.user
        only_mine = self.request.query_params.get("mine")  # TODO: deprecate
        only_pending = self.request.query_params.get("pending")

        all_structures = Structure.objects.select_related(
            "typology", "source", "parent"
        ).all()
        if only_mine:
            if not user or not user.is_authenticated:
                return Structure.objects.none()
            return (
                all_structures.filter(membership__user=user)
                .order_by("-modification_date")
                .distinct()
            )
        elif only_pending:
            if not user or not user.is_authenticated:
                return Structure.objects.none()
            return (
                all_structures.filter(putative_membership__user=user)
                .exclude(putative_membership__invited_by_admin=True)
                .order_by("-modification_date")
                .distinct()
            )

        else:
            return all_structures.order_by("-modification_date")

    def get_serializer_class(self):
        if self.action == "list":
            return StructureListSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        user = self.request.user
        source = (
            StructureSource.objects.get(value="equipe-dora")
            if user.is_staff
            else StructureSource.objects.get(value="porteur")
        )
        structure = serializer.save(creator=user, last_editor=user, source=source)
        # When creating a structure, the creator becomes member and administrator of this structure
        StructureMember.objects.create(user=user, structure=structure, is_admin=True)

        send_mattermost_notification(
            f":office: Nouvelle structure “{structure.name}” créée dans le departement : **{structure.department}**\n{settings.FRONTEND_URL}/structures/{structure.slug}"
        )
        send_moderation_email(
            "Nouvelle structure créée",
            f"Nouvelle structure <strong><a href='{structure.get_absolute_url()}'>“{structure.name}”</strong> créée dans le departement {structure.department}",
        )

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

            if user.is_authenticated and (user.is_staff or user.is_bizdev):
                return StructureMember.objects.filter(structure__slug=structure_slug)

            try:
                StructureMember.objects.get(
                    user_id=user.id, structure__slug=structure_slug
                )
            except StructureMember.DoesNotExist:
                raise exceptions.PermissionDenied

            return StructureMember.objects.filter(
                structure__slug=structure_slug, user__is_valid=True
            )
        else:
            if user.is_authenticated and (user.is_staff or user.is_bizdev):
                return StructureMember.objects.all()

            structures_belonging = StructureMember.objects.filter(
                user_id=user.id
            ).values_list("structure_id", flat=True)
            return StructureMember.objects.filter(structure_id__in=structures_belonging)


class StructurePutativeMemberViewset(viewsets.ModelViewSet):
    serializer_class = StructurePutativeMemberSerializer
    permission_classes = [StructurePutativeMemberPermission]

    def get_queryset(self):

        structure_slug = self.request.query_params.get("structure")
        user = self.request.user

        if self.action in ("list", "create"):
            # Can't list or create without passing ?structure_slug
            if structure_slug is None:
                return StructurePutativeMember.objects.none()

            if user.is_authenticated and (user.is_staff or user.is_bizdev):
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
            if user.is_authenticated and (user.is_staff or user.is_bizdev):
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
            user.start_onboarding()

        must_set_password = not user.has_usable_password()
        if must_set_password:
            # generate a new short term token for password reset
            # The invitation token will be deleted as soon as the user sets a password
            tmp_token = Token.objects.create(
                user=user, expiration=timezone.now() + settings.AUTH_LINK_EXPIRATION
            )
        else:
            with transaction.atomic(durable=True):
                membership = StructureMember.objects.create(
                    user=pm.user,
                    structure=pm.structure,
                    is_admin=pm.is_admin,
                )
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

        tmp_token = Token.objects.create(
            user=member.user,
            expiration=timezone.now() + settings.INVITATION_LINK_EXPIRATION,
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
        url_path="cancel-invite",
        permission_classes=[permissions.IsAuthenticated],
    )
    def cancel_invite(self, request, pk):
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

        member.delete()

        return Response(status=201)

    @action(
        detail=True,
        methods=["post"],
        url_path="accept-membership-request",
        permission_classes=[permissions.IsAuthenticated],
    )
    def accept_membership_request(self, request, pk):
        # TODO: add tests
        try:
            pm = StructurePutativeMember.objects.get(
                id=pk, user__is_valid=True, user__is_active=True
            )
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

        with transaction.atomic(durable=True):
            membership = StructureMember.objects.create(
                user=pm.user,
                structure=pm.structure,
                is_admin=pm.is_admin,
            )
            pm.delete()
            membership.notify_access_granted()

        return Response(status=201)

    @action(
        detail=True,
        methods=["post"],
        url_path="reject-membership-request",
        permission_classes=[permissions.IsAuthenticated],
    )
    def reject_membership_request(self, request, pk):
        # TODO: add tests
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

        pm.notify_access_rejected()
        pm.delete()

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
            {"value": c.value, "label": c.label}
            for c in StructureTypology.objects.all()
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
