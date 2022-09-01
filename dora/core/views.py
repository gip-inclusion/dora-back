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


@api_view()
@permission_classes([permissions.AllowAny])
def get_inclusion_connect_login_info(request):
    # https://security.stackexchange.com/questions/147529/openid-connect-nonce-replay-attack
    # https://stackoverflow.com/questions/46844285/difference-between-oauth-2-0-state-and-openid-nonce-parameter-why-state-cou
    # https://blogs.aaddevsup.xyz/2019/11/state-parameter-in-mvc-application/
    # https://stackoverflow.com/questions/35165793/what-attack-does-the-state-parameter-in-openid-connect-server-flow-prevent
    # https://stackoverflow.com/questions/53246830/how-nonce-and-state-parameters-are-stored-and-transmitted-in-identityserver4
    # https://stackoverflow.com/questions/46844285/difference-between-oauth-2-0-state-and-openid-nonce-parameter-why-state-cou/46859861#46859861
    state = get_random_string(32)
    nonce = get_random_string(32)

    cache.set(
        f"oidc-state-{state}",
        {
            "state": state,
            "nonce": nonce,
        },
    )
    return Response(
        {
            "url": f"{settings.IC_BASE_URL}auth?response_type=code&from=dora&client_id={settings.IC_CLIENT_ID}&scope=openid profile email&nonce={nonce}",
            "state": state,
        }
    )


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def get_inclusion_connect_user_info(request):
    code = request.data.get("code")
    state = request.data.get("state")
    redirect_uri = request.data.get("redirect_uri")

    stored_state = cache.get(f"oidc-state-{state}")
    assert stored_state["state"] == state
    stored_nonce = stored_state["nonce"]

    try:
        response = requests.post(
            url=f"{settings.IC_BASE_URL}token",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "client_id": settings.IC_CLIENT_ID,
                "client_secret": settings.IC_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )
        result = json.loads(response.content)

        id_token = result["id_token"]
        decoded_id_token = jwt.decode(id_token, options={"verify_signature": False})

        assert settings.IC_BASE_URL.startswith(decoded_id_token["iss"])
        assert settings.IC_CLIENT_ID in decoded_id_token["aud"]
        assert decoded_id_token["azp"] == settings.IC_CLIENT_ID
        assert int(decoded_id_token["exp"]) > time.time()
        assert stored_nonce and stored_nonce == decoded_id_token["nonce"]
        # TODO: valider le at_hash?

        user_dict = {
            "email": decoded_id_token["email"],
            "first_name": decoded_id_token["given_name"],
            "last_name": decoded_id_token["family_name"],
            "email_verified": decoded_id_token["email_verified"],
            "preferred_username": decoded_id_token["preferred_username"],
        }
        user = User.objects.get(email=user_dict["email"])
        update_last_login(user)
        token, _created = Token.objects.get_or_create(user=user, expiration=None)
        # TODO: maybe update firstname / lastname if applicable?
        return Response({"token": token.key, "valid_user": True})
    except requests.exceptions.RequestException as e:
        print("HTTP Request failed", e)
    # TODO: return error

    # La requete /userinfo n'est pas nécessaire pour le moment,
    # puisqu'on a toutes les informations nécessaires dans le id_token,
    # mais le code ressemblerait à :

    # access_token = result["access_token"]
    # response = requests.get(
    #     url=f"{settings.IC_BASE_URL}userinfo",
    #     headers={
    #         "Authorization": f"Bearer {access_token}",
    #     },
    # )
    # print(
    #     "Response HTTP Status Code: {status_code}".format(
    #         status_code=response.status_code
    #     )
    # )
    # result = json.loads(response.content)
