from django.contrib.auth.password_validation import password_changed, validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework import exceptions, permissions, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import User


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "newsletter",
            "phone_number",
        ]
        read_only_fields = ["email"]


@sensitive_post_parameters(["first_name", "last_name", "phone_number"])
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def update_profile(request):
    serializer = UserProfileSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    params = request.data
    for attr, value in serializer.validated_data.items():
        params.pop(attr)
        setattr(request.user, attr, value)
    if params:
        raise ValidationError(f"Invalid field(s): {', '.join(params.keys())}")
    request.user.save()
    return Response(UserProfileSerializer(request.user).data)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField()
    new_password = serializers.CharField()


@sensitive_post_parameters(["current_password", "new_password"])
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def password_change(request):
    serializer = PasswordChangeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    current_password = serializer.validated_data["current_password"]
    if not request.user.check_password(current_password):
        raise exceptions.PermissionDenied

    new_password = serializer.validated_data["new_password"]
    try:
        validate_password(new_password, request.user)
        request.user.set_password(new_password)
        request.user.save()
        password_changed(new_password, request.user)

        return Response(status=204)
    except DjangoValidationError:
        raise
