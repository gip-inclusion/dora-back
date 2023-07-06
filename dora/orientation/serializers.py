from rest_framework import serializers

from dora.orientation.models import Orientation
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
        required=False,
    )
    service = ServiceSerializer(read_only=True)

    prescriber_structure = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=Structure.objects.all(),
        required=False,
    )

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
            "orientation_reasons",
            "prescriber_structure",
            "processing_date",
            "processing_date",
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

    def get_service(self, orientation):
        service = Service.objects.filter(id=orientation.service_id).first()
        return ServiceSerializer(service).data
