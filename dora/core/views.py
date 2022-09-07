import json
import time

import jwt
import requests
from django.conf import settings
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404
from django.utils.crypto import get_random_string
from django.utils.text import get_valid_filename
from furl import furl
from rest_framework import permissions
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response

from dora.rest_auth.models import Token
from dora.rest_auth.views import update_last_login
from dora.services.models import Service
from dora.structures.models import Structure
from dora.users.models import User


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
        # TODO: valider le at_hash?

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
        except User.DoesNotExist:
            try:
                # On essaye de faire la correspondance avec un utilisateur existant
                # via son email, puis on le migre
                user = User.objects.get(email=user_dict["email"])
                if user.ic_id is not None:
                    # Il y a un conflit…
                    # TODO envoyer l'erreur vers Sentry, et informer l'utilisateur
                    assert False
                user.ic_id = user_dict["ic_id"]
                user.save()
            except User.DoesNotExist:
                user = User.objects.create(**user_dict)

        update_last_login(user)
        token, _created = Token.objects.get_or_create(user=user, expiration=None)
        # TODO: mettre à jour email, nom, prénom s'ils ont changé coté IC ?
        # TODO: mettre à jour la validité de l'email
        return Response({"token": token.key, "valid_user": True})
    except requests.exceptions.RequestException as e:
        print("HTTP Request failed", e)
        # TODO: return error
