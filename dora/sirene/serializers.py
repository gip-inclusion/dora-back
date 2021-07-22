from rest_framework import serializers

from .models import Establishment


class EstablishmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Establishment
        # Temporary, while working on the exact model content
        exclude = ()
