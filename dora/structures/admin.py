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
    extra = 0


class StructurePutativeMemberInline(admin.TabularInline):
    model = StructurePutativeMember
    extra = 0


class BranchInline(admin.TabularInline):
    model = Structure
    fields = ["siret", "name", "branch_id"]
    extra = 1
    verbose_name = "Antenne"
    verbose_name_plural = "Antennes"
    show_change_link = True

    def has_add_permission(self, request, obj):
        return obj.parent is None if obj else True


class IsBranchListFilter(admin.SimpleListFilter):
    title = "antenne"
    parameter_name = "is_branch"

    def lookups(self, request, model_admin):
        return (
            ("false", "Non"),
            ("true", "Oui"),
        )

    def queryset(self, request, queryset):
        if self.value() == "false":
            return queryset.filter(parent__isnull=True)
        if self.value() == "true":
            return queryset.filter(parent__isnull=False)


class StructureAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "slug",
        "parent",
        "department",
        "typology",
        "city_code",
        "city",
        "modification_date",
        "last_editor",
    ]
    list_filter = [IsBranchListFilter, "source", "typology", "department"]
    search_fields = ("name", "siret", "code_safir_pe", "city", "department", "slug")
    ordering = ["-modification_date", "department"]
    inlines = [StructureMemberInline, StructurePutativeMemberInline, BranchInline]
    readonly_fields = (
        "creation_date",
        "modification_date",
    )


admin.site.register(Structure, StructureAdmin)
admin.site.register(StructureMember, StructureMemberAdmin)
admin.site.register(StructurePutativeMember, StructurePutativeMemberAdmin)
admin.site.register(StructureSource, EnumAdmin)
admin.site.register(StructureTypology, EnumAdmin)
