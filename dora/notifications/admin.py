from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    raw_id_fields = ("owner_structure", "owner_user", "owner_structureputativemember")
    list_display = ("task_type", "created_at", "status")
    list_filter = ("task_type", "status")

