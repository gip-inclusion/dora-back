# Generated by Django 3.2.5 on 2021-08-24 09:04

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0009_auto_20210822_1420"),
    ]

    operations = [
        migrations.AlterField(
            model_name="service",
            name="subcategories",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(
                    choices=[
                        ("MO-FH", "Aide aux frais de déplacements"),
                        ("MO-CR", "Réparation de voitures à prix réduit"),
                    ],
                    max_length=6,
                ),
                size=None,
                verbose_name="Sous-catégorie",
            ),
        ),
    ]
