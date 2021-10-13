from django.contrib import admin
from django.contrib.admin.filters import RelatedOnlyFieldListFilter

from .models import Structure, StructureMember


class StructureMemberAdmin(admin.ModelAdmin):
    search_fields = (
        "user__name",
        "user__email",
        "structure__name",
        "structure__department",
    )

    list_display = [
        "user",
        "structure",
        "is_admin",
        "is_valid",
        "creation_date",
    ]
    list_filter = [
        "is_admin",
        "is_valid",
        ("structure", RelatedOnlyFieldListFilter),
    ]


class StructureMemberInline(admin.TabularInline):
    model = StructureMember
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
    search_fields = (
        "name",
        "siret",
        "code_safir_pe",
        "city",
        "department",
    )
    ordering = ["-modification_date", "department"]
    inlines = [StructureMemberInline]


admin.site.register(Structure, StructureAdmin)
admin.site.register(StructureMember, StructureMemberAdmin)
