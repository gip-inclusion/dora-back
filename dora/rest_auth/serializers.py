from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from dora.sirene.models import Establishment
from dora.structures.models import Structure
from dora.structures.serializers import StructureListSerializer
from dora.users.models import User


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if email and password:
            user = authenticate(
                request=self.context.get("request"),
                email=email,
                password=password,
            )

            # The authenticate call simply returns None for is_active=False
            # users. (Assuming the default ModelBackend authentication
            # backend.)
            if not user:
                msg = "Unable to log in with provided credentials."
                raise serializers.ValidationError(msg, code="authorization")
        else:
            msg = 'Must include "username" and "password".'
            raise serializers.ValidationError(msg, code="authorization")

        attrs["user"] = user
        return attrs


class UserInfoSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    short_name = serializers.CharField(source="get_short_name", read_only=True)
    structures = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "last_name",
            "first_name",
            "full_name",
            "short_name",
            "email",
            "phone_number",
            "newsletter",
            "is_staff",
            "is_bizdev",
            "structures",
        ]

    def get_structures(self, user):
        if not user or not user.is_authenticated:
            qs = Structure.objects.none()
        else:
            qs = Structure.objects.filter(membership__user=user)
        return StructureListSerializer(qs, many=True).data


class TokenSerializer(serializers.Serializer):
    key = serializers.CharField()


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    new_password = serializers.CharField()


class ResendEmailValidationSerializer(serializers.Serializer):
    email = serializers.EmailField()


class StructureAndUserSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField()
    siret = serializers.CharField()
    newsletter = serializers.BooleanField(default=False)

    def validate_email(self, value):
        try:
            User.objects.get(email=value)
            raise serializers.ValidationError("Cet utilisateur existe déjà")
        except User.DoesNotExist:
            return value

    def validate(self, attrs):
        first_name = attrs.get("first_name")
        last_name = attrs.get("last_name")
        email = attrs.get("email")
        password = attrs.get("password")
        siret = attrs.get("siret")
        tmp_user = User(first_name=first_name, last_name=last_name, email=email)

        try:
            validate_password(password, tmp_user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})

        try:
            establishment = Establishment.objects.get(siret=siret)
            attrs["establishment"] = establishment
        except Establishment.DoesNotExist:
            # The SIRET field is hidden on the frontend, so display this error globally
            # TODO: Ideally it should be the frontend role to display the message anyway
            raise serializers.ValidationError({"non_field_errors": "SIRET inconnu"})

        return super().validate(attrs)
