from rest_framework import serializers

from .models import Establishment


def clean_spaces(string):
    return string.replace("  ", " ").strip()


class EstablishmentSerializer(serializers.ModelSerializer):
    address1 = serializers.SerializerMethodField()
    address2 = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    postal_code = serializers.SerializerMethodField()
    city_code = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta:
        model = Establishment
        # Temporary, while working on the exact model content
        fields = [
            "address1",
            "address2",
            "ape",
            "city_code",
            "city",
            "latitude",
            "longitude",
            "name",
            "nic",
            "postal_code",
            "siren",
            "siret",
        ]

    def get_address1(self, obj):
        return clean_spaces(
            f"{obj.numero_voie} {obj.repetition_index} {obj.type_voie} {obj.libelle_voie}"
        )

    def get_address2(self, obj):
        return obj.complement_adresse

    def get_city(self, obj):
        return clean_spaces(
            f'{obj.libelle_cedex or obj.libelle_commune or ""} {obj.distribution_speciale or ""}'
        )

    def get_postal_code(self, obj):
        return obj.code_cedex or obj.code_postal

    def get_city_code(self, obj):
        return obj.code_commune

    def get_name(self, obj):
        sigle = f"({obj.sigle_parent})" if obj.sigle_parent else ""
        parent_name = clean_spaces(f"{obj.denomination_parent} {sigle}")

        denom = obj.denomination
        enseigne1 = obj.enseigne1 if obj.enseigne1 != obj.denomination else ""
        name = clean_spaces(f"{denom} {enseigne1} {obj.enseigne2} {obj.enseigne3}")

        if name.startswith(parent_name):
            parent_name = ""
        return clean_spaces(f"{parent_name} {name}")
