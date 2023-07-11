from rest_framework import serializers

from dora.orientations.models import Orientation
from dora.services.models import Service
from dora.structures.models import Structure


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = [
            "contact_email",
            "contact_name",
            "contact_phone",
            "name",
            "slug",
        ]


class OrientationSerializer(serializers.ModelSerializer):
    service_slug = serializers.SlugRelatedField(
        source="service",
        slug_field="slug",
        queryset=Service.objects.all(),
    )
    service = ServiceSerializer(read_only=True)

    prescriber_structure = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=Structure.objects.all(),
    )

    prescriber = serializers.SerializerMethodField()

    class Meta:
        model = Orientation
        fields = [
            "beneficiary_attachments",
            "beneficiary_availability",
            "beneficiary_contact_preferences",
            "beneficiary_email",
            "beneficiary_first_name",
            "beneficiary_last_name",
            "beneficiary_other_contact_method",
            "beneficiary_phone",
            "creation_date",
            "id",
            "orientation_reasons",
            "prescriber",
            "prescriber_structure",
            "processing_date",
            "processing_date",
            "query_id",
            "referent_email",
            "referent_first_name",
            "referent_last_name",
            "referent_phone",
            "requirements",
            "service",
            "service_slug",
            "situation",
            "situation_other",
            "status",
        ]

    def get_prescriber(self, orientation):
        return {
            "name": orientation.prescriber.get_full_name(),
            "email": orientation.prescriber.email,
        }
