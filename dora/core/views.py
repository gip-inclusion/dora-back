import json
import logging
import time
from datetime import timedelta

import jwt
import requests
from django.conf import settings
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.text import get_valid_filename
from furl import furl
from rest_framework import permissions
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.exceptions import APIException
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response

from dora.rest_auth.models import Token
from dora.rest_auth.views import update_last_login
from dora.services.models import Service
from dora.structures.models import Structure
from dora.users.models import User

logger = logging.getLogger(__name__)


@api_view(["POST"])
@parser_classes([FileUploadParser])
@permission_classes([permissions.AllowAny])
def upload(request, filename, structure_slug):
    # TODO: check that I have permission to upload to this service
    structure = get_object_or_404(Structure.objects.all(), slug=structure_slug)
    file_obj = request.data["file"]
    clean_filename = (
        f"{settings.ENVIRONMENT}/{structure.id}/{get_valid_filename(filename)}"
    )
    result = default_storage.save(clean_filename, file_obj)
    return Response({"key": result}, status=201)


@api_view()
@permission_classes([permissions.AllowAny])
def ping(request):
    check_services = Service.objects.exists()
    if check_services:
        return Response("ok", status=200)
    return Response("ko", status=500)


def trigger_error(request):
    division_by_zero = 1 / 0
    print(division_by_zero)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def inclusion_connect_get_login_info(request):
    redirect_uri = request.data.get("redirect_uri")
    login_hint = request.data.get("login_hint", "")
    state = get_random_string(32)
    nonce = get_random_string(32)

    cache.set(
        f"oidc-state-{state}",
        {"state": state, "nonce": nonce, "redirect_uri": redirect_uri},
    )
    query = {
        "response_type": "code",
        "from": "dora",
        "client_id": {settings.IC_CLIENT_ID},
        "scope": "openid profile email",
        "nonce": nonce,
        "state": state,
        "redirect_uri": redirect_uri,
        "login_hint": login_hint,
    }
    return Response(
        {
            "url": furl(settings.IC_AUTH_URL).add(query).url,
            "state": state,
        }
    )


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def inclusion_connect_get_logout_info(request):
    redirect_uri = request.data.get("redirect_uri")

    query = {
        "from": "dora",
        "client_id": {settings.IC_CLIENT_ID},
        "post_logout_redirect_uri": redirect_uri,
    }
    return Response(
        {
            "url": furl(settings.IC_LOGOUT_URL).add(query).url,
        }
    )


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def inclusion_connect_get_update_info(request):
    referrer_uri = request.data.get("referrer_uri")

    query = {
        "from": "dora",
        "referrer": {settings.IC_CLIENT_ID},
        "referrer_uri": referrer_uri,
    }
    return Response(
        {
            "url": furl(settings.IC_ACCOUNT_URL).add(query).url,
        }
    )


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def inclusion_connect_authenticate(request):
    code = request.data.get("code")
    state = request.data.get("state")
    frontend_state = request.data.get("frontend_state")
    stored_state = cache.get(f"oidc-state-{state}")
    assert stored_state["state"] == state == frontend_state

    stored_nonce = stored_state["nonce"]
    stored_redirect_uri = stored_state["redirect_uri"]

    try:
        response = requests.post(
            url=settings.IC_TOKEN_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "client_id": settings.IC_CLIENT_ID,
                "client_secret": settings.IC_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": stored_redirect_uri,
            },
        )
        result = json.loads(response.content)

        id_token = result["id_token"]
        decoded_id_token = jwt.decode(id_token, options={"verify_signature": False})

        assert decoded_id_token["iss"] == settings.IC_ISSUER_ID
        assert settings.IC_CLIENT_ID in decoded_id_token["aud"]
        assert decoded_id_token["azp"] == settings.IC_CLIENT_ID
        assert int(decoded_id_token["exp"]) > time.time()
        assert stored_nonce and stored_nonce == decoded_id_token["nonce"]

        user_dict = {
            "ic_id": decoded_id_token["sub"],
            "email": decoded_id_token["email"],
            "first_name": decoded_id_token["given_name"],
            "last_name": decoded_id_token["family_name"],
            "is_valid": decoded_id_token["email_verified"],
        }
        try:
            # On essaye de récupérer un utilisateur déjà migré
            user = User.objects.get(ic_id=user_dict["ic_id"])
            should_save = False
            if user.email != user_dict["email"]:
                user.email = user_dict["email"]
                should_save = True
            if user.first_name != user_dict["first_name"]:
                user.first_name = user_dict["first_name"]
                should_save = True
            if user.last_name != user_dict["last_name"]:
                user.last_name = user_dict["last_name"]
                should_save = True
            if user.is_valid != user_dict["is_valid"]:
                user.is_valid = user_dict["is_valid"]
                should_save = True
            if should_save:
                user.save()
        except User.DoesNotExist:
            try:
                # On essaye de faire la correspondance avec un utilisateur existant
                # via son email, puis on le migre
                user = User.objects.get(email=user_dict["email"])
                if user.ic_id is not None:
                    logging.error(
                        "Conflit avec Keycloak",
                        extra={
                            # Potentiel problème RGPD; en attente d'un avis du DPO.
                            # new_ic_id: user_dict["ic_id"],
                            # email: user.email,
                            # old_ic_id: user.ic_id
                        },
                    )
                    return APIException("Conflit avec le fournisseur d'identité")
                user.ic_id = user_dict["ic_id"]
                user.first_name = user_dict["first_name"]
                user.last_name = user_dict["last_name"]
                user.is_valid = user_dict["is_valid"]
                user.save()
            except User.DoesNotExist:
                user = User.objects.create(**user_dict)

        update_last_login(user)
        token, _created = Token.objects.get_or_create(
            user=user,
            expiration=timezone.now()
            + timedelta(days=settings.IC_EXPIRATION_DELAY_DAYS),
        )
        return Response({"token": token.key, "valid_user": True})
    except requests.exceptions.RequestException as e:
        logging.exception(e)
        return APIException("Erreur de communication avec le fournisseur d'identité")
