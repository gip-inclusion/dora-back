# Generated by Django 4.2.10 on 2024-02-29 16:04

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0103_savedsearch_location_kinds"),
    ]

    operations = [
        migrations.AddField(
            model_name="service",
            name="appointment_link",
            field=models.URLField(
                blank=True, verbose_name="Lien de prise de rendez-vous"
            ),
        ),
    ]
