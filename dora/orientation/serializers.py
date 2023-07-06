from rest_framework import serializers

from dora.orientation.models import Orientation
from dora.services.models import Service
from dora.structures.models import Structure


class OrientationSerializer(serializers.ModelSerializer):
    service = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    answer_date = serializers.SerializerMethodField()

    prescriber_structure = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=Structure.objects.all(),
        required=False,
    )

    class Meta:
        model = Orientation
        fields = [
            "id",
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
            "creation_date",
            "status",
            "answer_date",
            "prescriber_structure",
        ]

    def get_service(self, orientation):
        service = Service.objects.filter(id=orientation.service_id).first()
        return ServiceSerializer(service).data

    def get_status(self, orientation):
        # TODO
        return "PENDING"
        # return "ACCEPTED"
        # return "REFUSED"

    def get_answer_date(self, orientation):
        # TODO
        return "2023-07-05T17:39:47.903311+02:00"


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
