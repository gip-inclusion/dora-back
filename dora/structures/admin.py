from django.contrib import admin
from django.contrib.admin.filters import RelatedOnlyFieldListFilter

from dora.core.admin import EnumAdmin

from .models import (
    Structure,
    StructureMember,
    StructurePutativeMember,
    StructureSource,
    StructureTypology,
)


class StructurePutativeMemberAdmin(admin.ModelAdmin):
    search_fields = (
        "user__first_name",
        "user__last_name",
        "user__email",
        "structure__name",
        "structure__department",
    )

    list_display = [
        "user",
        "structure",
        "is_admin",
        "invited_by_admin",
        "creation_date",
    ]
    list_filter = [
        "is_admin",
        "invited_by_admin",
        ("structure", RelatedOnlyFieldListFilter),
    ]


class StructureMemberAdmin(admin.ModelAdmin):
    search_fields = (
        "user__first_name",
        "user__last_name",
        "user__email",
        "structure__name",
        "structure__department",
    )

    list_display = [
        "user",
        "structure",
        "is_admin",
        "creation_date",
    ]
    list_filter = [
        "is_admin",
        ("structure", RelatedOnlyFieldListFilter),
    ]


class StructureMemberInline(admin.TabularInline):
    model = StructureMember
    readonly_fields = ["user", "structure"]
    extra = 0

    def has_add_permission(self, request, obj):
        return False


class StructurePutativeMemberInline(admin.TabularInline):
    model = StructurePutativeMember
    readonly_fields = ["user", "structure"]
    extra = 0

    def has_add_permission(self, request, obj):
        return False


class StructureAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "slug",
        "department",
        "typology",
        "city_code",
        "city",
        "modification_date",
        "last_editor",
    ]
    list_filter = [
        "source",
        "typology",
        "department",
        "is_antenna",
    ]
    search_fields = ("name", "siret", "code_safir_pe", "city", "department", "slug")
    ordering = ["-modification_date", "department"]
    inlines = [StructureMemberInline, StructurePutativeMemberInline]


admin.site.register(Structure, StructureAdmin)
admin.site.register(StructureMember, StructureMemberAdmin)
admin.site.register(StructurePutativeMember, StructurePutativeMemberAdmin)
admin.site.register(StructureSource, EnumAdmin)
admin.site.register(StructureTypology, EnumAdmin)
