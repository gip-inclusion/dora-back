import random
from datetime import timedelta
from time import sleep

from django.contrib.auth.password_validation import password_changed, validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http.response import Http404
from django.utils import timezone
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework import exceptions, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from dora.rest_auth.authentication import TokenAuthentication
from dora.rest_auth.models import Token
from dora.rest_auth.serializers import (
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetSerializer,
    TokenSerializer,
)
from dora.structures.models import Structure, StructureMember
from dora.users.models import User

from .emails import send_email_validation_email, send_password_reset_email
from .serializers import ResendEmailValidationSerializer, ServiceAndUserSerializer


@sensitive_post_parameters(["password"])
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data["user"]
    if not user.is_valid:
        return Response({"valid_user": False})
    else:
        # We don't want to return expirable tokens, they are just here for password
        # resets !
        token, _created = Token.objects.get_or_create(user=user, expiration=None)
        return Response({"token": token.key, "valid_user": True})


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def password_reset(request):
    serializer = PasswordResetSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data["email"]
    try:
        user = User.objects.get(email=email)
        tmp_token = Token.objects.create(
            user=user, expiration=timezone.now() + timedelta(minutes=30)
        )
        send_password_reset_email(email, user.name, tmp_token.key)
        return Response(status=204)
    except User.DoesNotExist:
        # We don't want to expose the fact that the user doesn't exist
        # Introduce a random delay to simulate the time spend sending the mail
        sleep(random.random() * 1.5)
        return Response(status=204)


@sensitive_post_parameters(["new_password"])
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def password_reset_confirm(request):
    serializer = PasswordResetConfirmSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    new_password = serializer.validated_data["new_password"]
    try:
        validate_password(new_password, request.user)
        request.user.set_password(new_password)
        request.user.save()
        password_changed(new_password, request.user)
        # Cleanup all temporary tokens
        Token.objects.filter(user=request.user, expiration__isnull=False).delete()
        return Response(status=204)
    except DjangoValidationError:
        raise


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def token_verify(request):
    serializer = TokenSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    key = serializer.validated_data["key"]
    try:
        TokenAuthentication().authenticate_credentials(key)
    except exceptions.AuthenticationFailed:
        raise Http404

    return Response({"result": "ok"}, status=200)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@transaction.atomic
def validate_email(request):
    serializer = TokenSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    key = serializer.validated_data["key"]
    try:
        user, token = TokenAuthentication().authenticate_credentials(key)
        token.delete()
    except exceptions.AuthenticationFailed:
        raise Http404
    if not user.is_valid:
        user.is_valid = True
        user.save()

    return Response({"result": "ok"}, status=200)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def resend_validation_email(request):
    serializer = ResendEmailValidationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data["email"]
    try:
        user = User.objects.get(email=email)
        tmp_token = Token.objects.create(
            user=user, expiration=timezone.now() + timedelta(minutes=30)
        )
        send_email_validation_email(email, user.name, tmp_token.key)
        return Response(status=204)
    except User.DoesNotExist:
        # We don't want to expose the fact that the user doesn't exist
        # Introduce a random delay to simulate the time spend sending the mail
        sleep(random.random() * 1.5)
        return Response(status=204)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@transaction.atomic
def register_service_and_user(request):
    serializer = ServiceAndUserSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    data = serializer.validated_data

    # Create User
    user = User.objects.create_user(data["email"], data["password"], name=data["name"])

    # Create Structure
    establishment = data["establishment"]
    is_new_structure = False
    try:
        structure = Structure.objects.get(siret=establishment.siret)
    except Structure.DoesNotExist:
        structure = Structure.objects.create_from_establishment(establishment)
        is_new_structure = True
        structure.creator = user
        structure.last_editor = user
        structure.save()

    # Link them
    StructureMember.objects.create(
        user=user, structure=structure, is_admin=is_new_structure
    )

    # Send validation link email
    tmp_token = Token.objects.create(
        user=user, expiration=timezone.now() + timedelta(minutes=30)
    )
    send_email_validation_email(data["email"], user.name, tmp_token.key)
    return Response(status=201)
