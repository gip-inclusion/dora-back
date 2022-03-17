from django.contrib import admin

from dora.stats.models import DeploymentState


class DeploymentStateAdmin(admin.ModelAdmin):
    list_display = ("department_code", "department_name", "state")
    list_filter = ["state"]
    list_editable = ["state"]
    list_per_page = 101
    ordering = ["department_code"]
    readonly_fields = ["department_code", "department_name"]

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(DeploymentState, DeploymentStateAdmin)
