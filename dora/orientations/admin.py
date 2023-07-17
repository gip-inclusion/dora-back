from django.contrib import admin

from .models import Orientation, SentContactEmail


class SentContactEmailInline(admin.TabularInline):
    model = SentContactEmail
    max_num = 0
    can_delete = False
    readonly_fields = ("date_sent", "recipient", "carbon_copies")


class OrientationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "beneficiary_last_name",
        "service",
        "creation_date",
        "processing_date",
        "status",
    )
    list_filter = (
        "status",
        "creation_date",
        "processing_date",
    )
    raw_id_fields = (
        "prescriber",
        "prescriber_structure",
        "service",
    )
    date_hierarchy = "creation_date"
    ordering = ("-id",)
    readonly_fields = ("query_id", "original_service_name")
    filter_horizontal = ("rejection_reasons",)
    inlines = [SentContactEmailInline]


admin.site.register(Orientation, OrientationAdmin)
