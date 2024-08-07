import requests
from django.core.exceptions import SuspiciousOperation
from mozilla_django_oidc.auth import (
    OIDCAuthenticationBackend as MozillaOIDCAuthenticationBackend,
)


class OIDCError(Exception):
    """Exception générique pour les erreurs OIDC"""


class OIDCAuthenticationBackend(MozillaOIDCAuthenticationBackend):
    def get_userinfo(self, access_token, id_token, payload):
        # Surcharge de la récupération des informations utilisateur:
        # le décodage JSON du contenu JWT pose problème avec ProConnect
        # qui le retourne en format binaire (content-type: application/jwt)
        # d'où ce petit hack.
        # Inspiré de : https://github.com/numerique-gouv/people/blob/b637774179d94cecb0ef2454d4762750a6a5e8c0/src/backend/core/authentication/backends.py#L47C1-L47C57
        user_response = requests.get(
            self.OIDC_OP_USER_ENDPOINT,
            headers={"Authorization": "Bearer {0}".format(access_token)},
            verify=self.get_settings("OIDC_VERIFY_SSL", True),
            timeout=self.get_settings("OIDC_TIMEOUT", None),
            proxies=self.get_settings("OIDC_PROXY", None),
        )
        user_response.raise_for_status()

        try:
            # cas où le type du contenu est `application/json`
            return user_response.json()
        except requests.exceptions.JSONDecodeError:
            # sinon, on présume qu'il s'agit d'un contenu `application/jwt` (+...)
            # comme c'est le cas pour ProConnect
            return self.verify_token(user_response.text)

    def create_user(self, claims):
        # on peut à la rigueur se passer de certains élements contenus dans les claims,
        # mais pas de ceux-là :
        email, sub = claims.get("email"), claims.get("sub")
        if not email:
            raise SuspiciousOperation(
                "L'adresse e-mail n'est pas inclue dans les `claims`"
            )

        if not sub:
            raise SuspiciousOperation(
                "Le sujet (`sub`) n'est pas inclu dans les `claims`"
            )

        # TODO: le SIRET fait partie des claims obligatoire,
        # voir comment traiter les rattachements à une structure.
        # De plus, il semble que l'appartenance à plusieurs SIRET soit possible.

        # L'utilisateur est créé sans mot de passe (aucune connexion à l'admin),
        # et comme venant de ProConnect, on considère l'e-mail vérifié.
        return self.UserModel.objects.create_user(
            email,
            sub_pc=sub,
            first_name=claims.get("given_name", "N/D"),
            last_name=claims.get("usual_name", "N/D"),
            is_valid=True,
        )
