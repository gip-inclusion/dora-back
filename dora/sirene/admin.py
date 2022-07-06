from django.contrib import admin

from .models import Establishment


class EstablishmentAdmin(admin.ModelAdmin):
    list_display = ["name", "siren", "siret", "city", "city_code"]
    search_fields = ("full_search_text", "siret")


admin.site.register(Establishment, EstablishmentAdmin)
