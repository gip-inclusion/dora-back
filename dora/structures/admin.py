from django.contrib import admin

from .models import Structure


class StructureAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "slug",
        "modification_date",
        "last_editor",
    ]
    ordering = ["-modification_date"]


admin.site.register(Structure, StructureAdmin)
