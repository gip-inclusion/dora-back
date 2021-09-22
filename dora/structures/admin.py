from django.contrib import admin

from .models import Structure, StructureMember


class StructureMemberAdmin(admin.ModelAdmin):
    search_fields = (
        "user__name",
        "user__email",
        "structure__name",
        "structure__department",
    )

    list_display = ["user", "structure", "is_admin"]
    list_filter = ["is_admin"]


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
        "city_code",
        "city",
        "modification_date",
        "last_editor",
    ]
    list_filter = ["source", "department"]
    search_fields = ("name", "siret", "code_safir_pe", "city", "department")
    ordering = ["-modification_date", "department"]
    inlines = [StructureMemberInline]


admin.site.register(Structure, StructureAdmin)
admin.site.register(StructureMember, StructureMemberAdmin)
