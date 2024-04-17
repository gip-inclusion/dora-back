import logging

from django.contrib import admin

from .models import ActionLog


class LogLevelFilter(admin.SimpleListFilter):
    title = "niveau de log"
    parameter_name = "log_level"

    def lookups(self, request, model_admin):
        # attention à `_levelToName` qui a déjà changé de nom par le passé ...
        return [(v, v) for k, v in logging._levelToName.items()]

    def queryset(self, request, queryset):
        v = self.value()
        return queryset.filter(payload__level=v) if v else queryset


@admin.register(ActionLog)
class ActionLogAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "log_level")
    list_filter = (LogLevelFilter,)
    readonly_fields = ("id", "created_at", "log_level", "payload")
    search_fields = ("id",)
    ordering = ("-created_at",)

    def log_level(self, obj):
        return obj.payload.get("level")

    log_level.short_description = "niveau de log"
