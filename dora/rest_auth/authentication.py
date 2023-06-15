from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication as DRFTokenAuthentication

from .models import Token


class TokenAuthentication(DRFTokenAuthentication):
    model = Token

    def authenticate_credentials(self, key):
        model = self.get_model()

        token = model.objects.select_related("user").filter(key=key).first()
        if not token:
            raise exceptions.AuthenticationFailed("Token invalide.")

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed("Token invalide")

        return (token.user, token)
