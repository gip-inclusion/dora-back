from django.core.files.storage import default_storage
from rest_framework import serializers

from dora.structures.models import Structure

from .models import Service


class ServiceSerializer(serializers.ModelSerializer):
    forms_info = serializers.SerializerMethodField()
    structure = serializers.SlugRelatedField(
        queryset=Structure.objects.all(), slug_field="slug"
    )

    class Meta:
        model = Service
        # Temporary, while working on the exact model content
        fields = "__all__"
        lookup_field = "slug"

    def get_forms_info(self, obj):
        forms = [{"name": form, "url": default_storage.url(form)} for form in obj.forms]
        return forms
