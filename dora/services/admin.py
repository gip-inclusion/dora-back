from django.contrib.admin import RelatedOnlyFieldListFilter
from django.contrib.gis import admin

from dora.core.admin import EnumAdmin

from .models import (
    AccessCondition,
    BeneficiaryAccessMode,
    CoachOrientationMode,
    ConcernedPublic,
    Credential,
    LocationKind,
    Requirement,
    Service,
    ServiceCategory,
    ServiceKind,
    ServiceModificationHistoryItem,
    ServiceSubCategory,
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
        "creation_date",
        "modification_date",
        "publication_date",
        "last_editor",
        "is_draft",
        "is_suggestion",
    ]
    list_filter = [
        "is_draft",
        "is_suggestion",
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

admin.site.register(BeneficiaryAccessMode, EnumAdmin)
admin.site.register(CoachOrientationMode, EnumAdmin)
admin.site.register(LocationKind, EnumAdmin)
admin.site.register(ServiceCategory, EnumAdmin)
admin.site.register(ServiceKind, EnumAdmin)
admin.site.register(ServiceSubCategory, EnumAdmin)
