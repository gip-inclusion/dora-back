from rest_framework import serializers

from .models import Service


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        # Temporary, while working on the exact model content
        fields = "__all__"
