# Generated by Django 4.2.10 on 2024-04-17 17:18

import uuid

import django.contrib.postgres.indexes
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ActionLog",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name="identifiant",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now=True, verbose_name="date de création"
                    ),
                ),
                (
                    "payload",
                    models.JSONField(
                        blank=True, default=dict, verbose_name="contenu brut (JSON)"
                    ),
                ),
            ],
            options={
                "verbose_name": "historique des actions",
                "verbose_name_plural": "historique des actions",
                "indexes": [
                    django.contrib.postgres.indexes.BrinIndex(
                        autosummarize=True,
                        fields=["created_at"],
                        name="idx_logs_actionlog_created_at",
                    )
                ],
            },
        ),
    ]
