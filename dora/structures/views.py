from datetime import timedelta

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import exceptions, mixins, permissions, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from dora.core.notify import send_mattermost_notification
from dora.rest_auth.authentication import TokenAuthentication
from dora.rest_auth.models import Token
from dora.structures.emails import send_invitation_email
from dora.structures.models import (
    Structure,
    StructureMember,
    StructureSource,
    StructureTypology,
)
from dora.structures.permissions import StructureMemberPermission, StructurePermission

from .serializers import (
    InviteSerializer,
    SiretClaimedSerializer,
    StructureListSerializer,
    StructureMemberSerializer,
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

    def get_queryset(self):
        user = self.request.user
        only_mine = self.request.query_params.get("mine")

        if only_mine:
            return (
                self.get_my_structures(user).order_by("-modification_date").distinct()
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

    def perform_update(self, serializer):
        serializer.save(last_editor=self.request.user)

    @action(
        detail=False,
        methods=["post"],
        url_path="accept-invite",
        permission_classes=[permissions.AllowAny],
    )
    def accept_invite(self, request):
        serializer = InviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        key = serializer.validated_data["key"]
        member_id = serializer.validated_data["member"]

        try:
            token_user, token = TokenAuthentication().authenticate_credentials(key)

        except exceptions.AuthenticationFailed:
            raise exceptions.PermissionDenied
        try:
            member = StructureMember.objects.get(id=member_id)
        except StructureMember.DoesNotExist:
            raise exceptions.PermissionDenied

        if member.user.id != token_user.id:
            raise exceptions.PermissionDenied

        if not token_user.is_valid:
            token_user.is_valid = True
            token_user.save()

        if not member.is_valid:
            member.is_valid = True
            member.save()

        must_set_password = not token_user.has_usable_password()
        if must_set_password:
            # generate a new short term token for password reset
            # The invitation token will be deleted as soon as the user sets a password
            tmp_token = Token.objects.create(
                user=token_user, expiration=timezone.now() + timedelta(minutes=30)
            )
        else:
            # The user already exists and hopefully know its password
            # we can safely delete the invitation token
            token.delete()

        return Response(
            {
                "structure_name": member.structure.name,
                "must_set_password": must_set_password,
                "token": tmp_token.key if must_set_password else None,
            },
            status=200,
        )


class StructureMemberViewset(viewsets.ModelViewSet):
    serializer_class = StructureMemberSerializer
    permission_classes = [StructureMemberPermission]

    def get_queryset(self):

        structure_slug = self.request.query_params.get("structure")
        user = self.request.user

        if self.action in ("list", "create"):
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

    @action(
        detail=True,
        methods=["post"],
        url_path="resend-invite",
        permission_classes=[permissions.IsAuthenticated],
    )
    def resend_invite(self, request, pk):
        try:
            member = StructureMember.objects.get(id=pk)
        except StructureMember.DoesNotExist:
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

        # Can't reinvite a valid user
        if member.is_valid and member.user.has_usable_password():
            raise exceptions.PermissionDenied

        tmp_token = Token.objects.create(
            user=member.user, expiration=timezone.now() + timedelta(days=7)
        )
        send_invitation_email(
            member,
            request_user.get_full_name(),
            tmp_token.key,
        )
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
