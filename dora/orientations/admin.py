from django.contrib import admin

from .models import Orientation


class OrientationAdmin(admin.ModelAdmin):
    list_display = ("id", "creation_date", "beneficiary_last_name", "service")
    raw_id_fields = (
        "prescriber",
        "prescriber_structure",
        "service",
    )
    date_hierarchy = "creation_date"
    ordering = ("-id",)
    readonly_fields = ("query_id",)


admin.site.register(Orientation, OrientationAdmin)
