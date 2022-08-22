# Generated by Django 4.0.6 on 2022-08-17 12:57

from django.db import migrations

from ..enums import ServiceStatus


def convert_history(apps, schema_editor):
    ServiceModificationHistoryItem = apps.get_model(
        "services", "ServiceModificationHistoryItem"
    )
    LogItem = apps.get_model("core", "LogItem")

    history_items = ServiceModificationHistoryItem.objects.filter(
        status=ServiceStatus.PUBLISHED
    )
    for hi in history_items:
        msg = f"Service modifié ({' / '.join(hi.fields)})"
        li = LogItem.objects.create(service=hi.service, user=hi.user, message=msg)
        LogItem.objects.filter(pk=li.pk).update(date=hi.date)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_initial"),
        ("services", "0070_init_moderation_status"),
    ]

    operations = [
        migrations.RunPython(convert_history, reverse_code=migrations.RunPython.noop)
    ]
