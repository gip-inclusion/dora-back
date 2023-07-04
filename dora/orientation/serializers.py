from rest_framework import serializers

from dora.orientation.models import Orientation
from dora.services.models import Service
from dora.structures.models import Structure


class OrientationSerializer(serializers.ModelSerializer):
    service = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=Service.objects.all(),
        required=False,
    )
    prescriber_structure = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=Structure.objects.all(),
        required=False,
    )

    class Meta:
        model = Orientation
        fields = [
            "situation",
            "situation_other",
            "requirements",
            "referent_last_name",
            "referent_first_name",
            "referent_phone",
            "referent_email",
            "beneficiary_last_name",
            "beneficiary_first_name",
            "beneficiary_contact_preferences",
            "beneficiary_phone",
            "beneficiary_email",
            "beneficiary_other_contact_method",
            "beneficiary_availability",
            "beneficiary_attachments",
            "orientation_reasons",
            "service",
            "prescriber_structure",
        ]
