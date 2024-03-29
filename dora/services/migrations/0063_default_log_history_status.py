# Generated by Django 4.0.6 on 2022-07-20 14:03

from django.db import migrations


def set_default_log_history_status(apps, schema_editor):
    ServiceModificationHistoryItem = apps.get_model(
        "services", "ServiceModificationHistoryItem"
    )
    ServiceModificationHistoryItem.objects.filter(service__is_model=False).update(
        status="PUBLISHED"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0062_add_status_to_log_history"),
    ]

    operations = [
        migrations.RunPython(
            set_default_log_history_status, reverse_code=migrations.RunPython.noop
        )
    ]
