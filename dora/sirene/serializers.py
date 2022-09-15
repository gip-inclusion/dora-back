from rest_framework import serializers

from .models import Establishment


class EstablishmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Establishment
        fields = [
            "address1",
            "address2",
            "ape",
            "city_code",
            "city",
            "latitude",
            "longitude",
            "name",
            "postal_code",
            "siren",
            "siret",
            "is_siege",
        ]
