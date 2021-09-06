from django.contrib.admin import RelatedOnlyFieldListFilter
from django.contrib.gis import admin

from .models import AccessCondition, ConcernedPublic, Credential, Requirement, Service


class ServiceAdmin(admin.OSMGeoAdmin):

    list_display = [
        "name",
        "slug",
        "structure",
        "category",
        "modification_date",
        "last_editor",
    ]
    list_filter = [
        ("structure", RelatedOnlyFieldListFilter),
    ]
    ordering = ["-modification_date"]


admin.site.register(Service, ServiceAdmin)
admin.site.register(AccessCondition)
admin.site.register(ConcernedPublic)
admin.site.register(Requirement)
admin.site.register(Credential)
