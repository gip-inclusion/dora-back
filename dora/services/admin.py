from django.contrib.admin import RelatedOnlyFieldListFilter
from django.contrib.gis import admin

from .models import (
    AccessCondition,
    ConcernedPublic,
    Credential,
    Requirement,
    Service,
    ServiceModificationHistoryItem,
)


class ServiceModificationHistoryItemInline(admin.TabularInline):
    model = ServiceModificationHistoryItem
    readonly_fields = ["user", "date", "fields"]
    extra = 0

    def has_add_permission(self, request, obj):
        return False


class ServiceAdmin(admin.OSMGeoAdmin):
    search_fields = (
        "name",
        "structure__name",
        "slug",
    )
    list_display = [
        "name",
        "slug",
        "structure",
        "category",
        "creation_date",
        "modification_date",
        "publication_date",
        "last_editor",
    ]
    list_filter = [
        ("structure", RelatedOnlyFieldListFilter),
    ]
    inlines = [ServiceModificationHistoryItemInline]
    ordering = ["-modification_date"]
    save_as = True


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
