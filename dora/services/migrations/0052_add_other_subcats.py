# Generated by Django 4.0.4 on 2022-06-06 12:04

from django.db import migrations


def add_other_subcats(apps, schema_editor):
    ServiceCategory = apps.get_model("services", "ServiceCategory")
    ServiceSubCategory = apps.get_model("services", "ServiceSubCategory")

    for category in ServiceCategory.objects.all():
        ServiceSubCategory.objects.get_or_create(
            value=f"{category.value}--autre", defaults={"label": "Autre"}
        )


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0051_service_last_sync_checksum_service_sync_checksum_and_more"),
    ]

    operations = [
        migrations.RunPython(add_other_subcats, reverse_code=migrations.RunPython.noop),
    ]
