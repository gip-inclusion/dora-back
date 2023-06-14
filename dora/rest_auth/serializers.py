from rest_framework import serializers

from dora.services.models import Bookmark
from dora.services.serializers import ServiceListSerializer
from dora.sirene.models import Establishment
from dora.structures.models import Structure
from dora.structures.serializers import StructureListSerializer
from dora.users.models import User


class BookmarkListSerializer(serializers.ModelSerializer):
    service = ServiceListSerializer(read_only=True)

    class Meta:
        model = Bookmark
        fields = ["service", "creation_date"]


class UserInfoSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    short_name = serializers.CharField(source="get_short_name", read_only=True)
    structures = serializers.SerializerMethodField()
    pending_structures = serializers.SerializerMethodField()
    bookmarks = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "bookmarks",
            "department",
            "email",
            "first_name",
            "full_name",
            "is_manager",
            "is_staff",
            "last_name",
            "newsletter",
            "pending_structures",
            "short_name",
            "structures",
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

    def get_bookmarks(self, user):
        if not user or not user.is_authenticated:
            qs = Bookmark.objects.none()
        else:
            qs = Bookmark.objects.filter(user=user).order_by("-creation_date")
        return BookmarkListSerializer(qs, many=True).data


class TokenSerializer(serializers.Serializer):
    key = serializers.CharField()


class JoinStructureSerializer(serializers.Serializer):
    siret = serializers.CharField(required=False)
    structure_slug = serializers.CharField(required=False)

    def validate(self, data):
        siret = data.get("siret")
        structure_slug = data.get("structure_slug")
        if siret and structure_slug:
            raise serializers.ValidationError(
                "Expecting only one of `siret` and `structure_slug`"
            )
        if siret:
            try:
                establishment = Establishment.objects.get(siret=siret)
                data["establishment"] = establishment
            except Establishment.DoesNotExist:
                # The field is hidden on the frontend, so display this error globally
                # TODO: Ideally it should be the frontend role to display the message anyway
                raise serializers.ValidationError({"non_field_errors": "SIRET inconnu"})
        else:
            try:
                structure = Structure.objects.get(slug=structure_slug)
                data["structure"] = structure
            except Structure.DoesNotExist:
                # The field is hidden on the frontend, so display this error globally
                # TODO: Ideally it should be the frontend role to display the message anyway
                raise serializers.ValidationError(
                    {"non_field_errors": "structure inconnue"}
                )
        return super().validate(data)
