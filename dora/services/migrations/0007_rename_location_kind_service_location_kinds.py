# Generated by Django 3.2.5 on 2021-08-20 10:02

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0006_auto_20210819_1608"),
    ]

    operations = [
        migrations.RenameField(
            model_name="service",
            old_name="location_kind",
            new_name="location_kinds",
        ),
    ]
