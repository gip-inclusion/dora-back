from django.contrib.gis import admin

from .models import ServiceSuggestion


class ServiceSuggestionAdmin(admin.OSMGeoAdmin):
    search_fields = (
        "name",
        "siret",
    )
    list_display = [
        "name",
        "siret",
        "creation_date",
    ]


admin.site.register(ServiceSuggestion, ServiceSuggestionAdmin)
