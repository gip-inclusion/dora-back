from rest_framework import serializers

from .models import Structure


class StructureSerializer(serializers.ModelSerializer):
    typology_display = serializers.CharField(source="get_typology_display")

    class Meta:
        model = Structure
        # Temporary, while working on the exact model content
        fields = "__all__"
        lookup_field = "slug"


class SiretClaimedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Structure
        fields = ["id", "siret", "slug"]
        lookup_field = "siret"
