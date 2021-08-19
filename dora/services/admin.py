from django.contrib import admin

from .models import AccessCondition, ConcernedPublic, Credential, Requirement, Service


class ServiceAdmin(admin.ModelAdmin):

    list_display = [
        "name",
        "slug",
        "structure",
        "modification_date",
        "last_editor",
    ]
    list_filter = [
        ("structure", admin.RelatedOnlyFieldListFilter),
    ]
    ordering = ["-modification_date"]


admin.site.register(Service, ServiceAdmin)
admin.site.register(AccessCondition)
admin.site.register(ConcernedPublic)
admin.site.register(Requirement)
admin.site.register(Credential)
