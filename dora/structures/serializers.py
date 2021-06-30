from rest_framework import serializers

from .models import Structure


class StructureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Structure
        # Temporary, while working on the exact model content
        fields = "__all__"
