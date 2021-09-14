from django.http.response import Http404
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from dora.rest_auth.models import Token
from dora.rest_auth.serializers import LoginSerializer, TokenSerializer


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data["user"]
    token, _created = Token.objects.get_or_create(user=user)
    return Response({"token": token.key})


@api_view()
# @permission_classes()
def password_reset(request):
    pass


@api_view()
# @permission_classes()
def password_confirm(request):
    pass


@api_view()
# @permission_classes()
def password_change(request):
    pass


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def token_verify(request):
    serializer = TokenSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    key = serializer.validated_data["key"]
    try:
        Token.objects.get(key=key)
    except Token.DoesNotExist:
        raise Http404

    return Response({"result": "ok"}, status=200)


@api_view()
# @permission_classes()
def register(request):
    pass


@api_view()
# @permission_classes()
def verify_email(request):
    pass


@api_view()
# @permission_classes()
def resend_email(request):
    pass
