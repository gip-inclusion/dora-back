from django.contrib import admin

from .models import Structure


class StructureAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]


admin.site.register(Structure, StructureAdmin)
