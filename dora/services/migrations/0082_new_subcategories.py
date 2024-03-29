# Generated by Django 4.0.8 on 2022-10-24 16:08

from django.db import migrations

from dora.services.migration_utils import create_subcategory


def add_subcategories(apps, schema_editor):
    ServiceSubCategory = apps.get_model("services", "ServiceSubCategory")

    create_subcategory(
        ServiceSubCategory,
        value="numerique--prendre-en-main-un-ordinateur",
        label="Prendre en main un ordinateur",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0081_new_fees_type"),
    ]

    operations = [
        migrations.RunPython(add_subcategories, reverse_code=migrations.RunPython.noop),
    ]
