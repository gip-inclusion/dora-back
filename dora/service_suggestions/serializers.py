import logging

from rest_framework import serializers

from .models import ServiceSuggestion

logger = logging.getLogger(__name__)


class ServiceSuggestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceSuggestion

        fields = ["name", "siret", "contents"]
