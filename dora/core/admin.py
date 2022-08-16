from django.contrib import admin

from .models import LogItem


class EnumAdmin(admin.ModelAdmin):
    list_display = [
        "value",
        "label",
    ]
    search_fields = (
        "value",
        "label",
    )
    ordering = ["label"]


class LogItemAdmin(admin.ModelAdmin):
    list_display = ["service", "structure", "user", "message"]
    readonly_fields = ["date"]


admin.site.register(LogItem, LogItemAdmin)
