from django.contrib import admin

from .models import Establishment


class EstablishmentAdmin(admin.ModelAdmin):
    show_full_result_count = False
    list_display = ["name", "siren", "siret", "city", "city_code"]
    search_help_text = "Recherche par nom, siren, ou siret"
    search_fields = (
        "siret__exact",
        "siren__exact",
        "full_search_text",
    )


admin.site.register(Establishment, EstablishmentAdmin)
