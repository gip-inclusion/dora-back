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


class CustomizableChoiceAdmin(admin.ModelAdmin):
    list_display = ("name", "structure")
    list_filter = [
        ("structure", RelatedOnlyFieldListFilter),
    ]


admin.site.register(Service, ServiceAdmin)
admin.site.register(AccessCondition, CustomizableChoiceAdmin)
admin.site.register(ConcernedPublic, CustomizableChoiceAdmin)
admin.site.register(Requirement, CustomizableChoiceAdmin)
admin.site.register(Credential, CustomizableChoiceAdmin)
