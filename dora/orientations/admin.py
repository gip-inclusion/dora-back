from django.contrib import admin, messages

from .checks import check_orientation, format_warnings
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
        "prescriber_email",
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

    @admin.display(description="e-mail prescripteur")
    def prescriber_email(self, obj):
        if p := obj.prescriber:
            return p.email
        return "-"

    def get_object(self, request, obj_id, f):
        # quelques tests pour notifier d'avertissements concernant la demande l'orientation (ou pas)
        if msgs := check_orientation(obj_id):
            self.message_user(request, format_warnings(msgs), messages.WARNING)

        return super().get_object(request, obj_id, f)


admin.site.register(Orientation, OrientationAdmin)
