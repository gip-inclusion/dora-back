from django.core.files.storage import default_storage
from rest_framework import serializers

from .models import Service


class ServiceSerializer(serializers.ModelSerializer):
    forms_info = serializers.SerializerMethodField()

    class Meta:
        model = Service
        # Temporary, while working on the exact model content
        fields = "__all__"

    def get_forms_info(self, obj):
        forms = [{"name": form, "url": default_storage.url(form)} for form in obj.forms]
        return forms
