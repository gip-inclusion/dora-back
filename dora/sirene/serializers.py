from rest_framework import serializers

from .models import Establishment


class EstablishmentSerializer(serializers.ModelSerializer):
    is_pole_emploi = serializers.SerializerMethodField()

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
            "is_pole_emploi",
        ]

    def get_is_pole_emploi(self, obj):
        from dora.structures.models import Structure, StructureTypology

        try:
            structure = Structure.objects.get(siret=obj.siret)
            return structure.typology == StructureTypology.objects.get(value="PE")
        except Structure.DoesNotExist:
            return False
