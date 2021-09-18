from django.contrib import admin

from .models import Structure, StructureMember


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
        "modification_date",
        "last_editor",
    ]
    ordering = ["-modification_date"]
    inlines = [StructureMemberInline]


admin.site.register(Structure, StructureAdmin)
