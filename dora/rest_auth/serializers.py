from rest_framework import serializers

from dora.services.models import (
    Alert,
    AlertFrequency,
    Bookmark,
    ServiceCategory,
    ServiceFee,
    ServiceKind,
    ServiceSubCategory,
)
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


class AlertListSerializer(serializers.ModelSerializer):
    categories = serializers.SlugRelatedField(
        slug_field="value",
        queryset=ServiceCategory.objects.all(),
        many=True,
        required=False,
    )
    categories_display = serializers.SlugRelatedField(
        source="categories", slug_field="label", many=True, read_only=True
    )

    subcategories = serializers.SlugRelatedField(
        slug_field="value",
        queryset=ServiceSubCategory.objects.all(),
        many=True,
        required=False,
    )
    subcategories_display = serializers.SlugRelatedField(
        source="subcategories", slug_field="label", many=True, read_only=True
    )

    kinds = serializers.SlugRelatedField(
        slug_field="value",
        queryset=ServiceKind.objects.all(),
        many=True,
        required=False,
    )
    kinds_display = serializers.SlugRelatedField(
        source="kinds", slug_field="label", many=True, read_only=True
    )

    fees = serializers.SlugRelatedField(
        slug_field="value",
        queryset=ServiceFee.objects.all(),
        many=True,
        required=False,
    )
    fees_display = serializers.SlugRelatedField(
        source="fees", slug_field="label", many=True, read_only=True
    )

    frequency = serializers.SlugRelatedField(
        slug_field="value",
        queryset=AlertFrequency.objects.all(),
        many=False,
        required=True,
    )

    class Meta:
        model = Alert
        fields = [
            "id",
            "city_label",
            "city_code",
            "categories",
            "categories_display",
            "subcategories",
            "subcategories_display",
            "kinds",
            "kinds_display",
            "fees",
            "fees_display",
            "frequency",
            "creation_date",
        ]


class UserInfoSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    short_name = serializers.CharField(source="get_short_name", read_only=True)
    structures = serializers.SerializerMethodField()
    pending_structures = serializers.SerializerMethodField()
    bookmarks = serializers.SerializerMethodField()
    alerts = serializers.SerializerMethodField()

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
            "alerts",
            "short_name",
            "structures",
            "main_activity",
            "cgu_versions_accepted",
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

    def get_alerts(self, user):
        if not user or not user.is_authenticated:
            qs = Alert.objects.none()
        else:
            qs = Alert.objects.filter(user=user).order_by("-creation_date")
        return AlertListSerializer(qs, many=True).data


class TokenSerializer(serializers.Serializer):
    key = serializers.CharField()


class JoinStructureSerializer(serializers.Serializer):
    siret = serializers.CharField(required=False)
    structure_slug = serializers.CharField(required=False)
    cgu_version = serializers.CharField(required=True)

    def validate(self, data):
        siret = data.get("siret")
        structure_slug = data.get("structure_slug")
        if siret and structure_slug:
            raise serializers.ValidationError(
                "`siret` et `structure_slug` ne peuvent être présents simultanément"
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
