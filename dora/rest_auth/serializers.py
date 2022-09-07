from rest_framework import serializers

from dora.sirene.models import Establishment
from dora.structures.models import Structure
from dora.structures.serializers import StructureListSerializer
from dora.users.models import User


class UserInfoSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    short_name = serializers.CharField(source="get_short_name", read_only=True)
    structures = serializers.SerializerMethodField()
    pending_structures = serializers.SerializerMethodField()

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
            "pending_structures",
        ]

    def get_structures(self, user):
        if not user or not user.is_authenticated:
            qs = Structure.objects.none()
        else:
            qs = Structure.objects.filter(membership__user=user)
        return StructureListSerializer(qs, many=True).data

    def get_pending_structures(self, user):
        if not user or not user.is_authenticated:
            qs = Structure.objects.none()
        else:
            qs = Structure.objects.filter(
                putative_membership__user=user,
                putative_membership__invited_by_admin=False,
            )
        return StructureListSerializer(qs, many=True).data


class TokenSerializer(serializers.Serializer):
    key = serializers.CharField()


class SiretSerializer(serializers.Serializer):
    siret = serializers.CharField()

    def validate(self, attrs):
        siret = attrs.get("siret")
        try:
            establishment = Establishment.objects.get(siret=siret)
            attrs["establishment"] = establishment
        except Establishment.DoesNotExist:
            # The SIRET field is hidden on the frontend, so display this error globally
            # TODO: Ideally it should be the frontend role to display the message anyway
            raise serializers.ValidationError({"non_field_errors": "SIRET inconnu"})

        return super().validate(attrs)
