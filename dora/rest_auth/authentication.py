from rest_framework.authentication import TokenAuthentication as DRFTokenAuthentication

from .models import Token


class TokenAuthentication(DRFTokenAuthentication):
    model = Token
