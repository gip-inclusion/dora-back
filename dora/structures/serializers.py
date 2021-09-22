from rest_framework import serializers

from .models import Structure


class StructureSerializer(serializers.ModelSerializer):
    typology_display = serializers.CharField(
        source="get_typology_display", read_only=True
    )

    class Meta:
        model = Structure
        fields = [
            "siret",
            "code_safir_pe",
            "typology",
            "typology_display",
            "slug",
            "name",
            "short_desc",
            "url",
            "full_desc",
            "facebook_url",
            "linkedin_url",
            "twitter_url",
            "youtube_url",
            "instagram_url",
            "ressources_url",
            "phone",
            "faq_url",
            "contact_form_url",
            "email",
            "postal_code",
            "city_code",
            "city",
            "department",
            "address1",
            "address2",
            "has_services",
            "ape",
            "longitude",
            "latitude",
            "creation_date",
            "modification_date",
        ]
        lookup_field = "slug"


class StructureListSerializer(StructureSerializer):
    num_services = serializers.SerializerMethodField()

    class Meta:
        model = Structure
        fields = ["slug", "name", "department", "typology_display", "num_services"]
        lookup_field = "slug"

    def get_num_services(self, obj):
        return obj.services.count()


class SiretClaimedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Structure
        fields = ["siret", "slug"]
        lookup_field = "siret"
