# Generated by Django 3.2.5 on 2021-09-06 14:49

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0019_datamigration_geom"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="service",
            name="latitude",
        ),
        migrations.RemoveField(
            model_name="service",
            name="longitude",
        ),
    ]
