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
        "orientation_checked",
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
    readonly_fields = ("query_id", "query_expires_at", "original_service_name")
    filter_horizontal = ("rejection_reasons",)
    inlines = [SentContactEmailInline]

    @admin.display(description="e-mail prescripteur")
    def prescriber_email(self, obj) -> str:
        if p := obj.prescriber:
            return p.email
        return "-"

    @admin.display(description="vérification")
    def orientation_checked(self, obj) -> bool:
        return not bool(check_orientation(obj))

    orientation_checked.boolean = True

    def get_object(self, request, obj_id, f):
        # quelques tests pour notifier d'avertissements concernant la demande l'orientation (ou pas)
        orientation = super().get_object(request, obj_id, f)

        if msgs := check_orientation(orientation):
            self.message_user(request, format_warnings(msgs), messages.WARNING)

        return orientation

    def get_queryset(self, request):
        qs = (
            super()
            .get_queryset(request)
            .prefetch_related(
                "prescriber_structure__membership", "service__structure__membership"
            )
            .select_related(
                "prescriber", "prescriber_structure", "service", "service__structure"
            )
        )
        return qs


admin.site.register(Orientation, OrientationAdmin)
