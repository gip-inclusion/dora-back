from rest_framework import serializers

from .models import Structure


class StructureSerializer(serializers.ModelSerializer):
    typology_display = serializers.CharField(
        source="get_typology_display", read_only=True
    )

    class Meta:
        model = Structure
        # Temporary, while working on the exact model content
        fields = "__all__"
        lookup_field = "slug"


class StructureListSerializer(serializers.ModelSerializer):
    department = serializers.SerializerMethodField()

    class Meta:
        model = Structure
        # Temporary, while working on the exact model content
        fields = ["slug", "name", "department"]
        lookup_field = "slug"

    def get_department(self, obj):
        return obj.postal_code[0:2]


class SiretClaimedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Structure
        fields = ["id", "siret", "slug"]
        lookup_field = "siret"
