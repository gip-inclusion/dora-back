# Generated by Django 4.2.10 on 2024-04-22 10:12

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
                    "level",
                    models.SmallIntegerField(
                        blank=True, editable=False, verbose_name="niveau de log"
                    ),
                ),
                ("msg", models.TextField(blank=True, verbose_name="message")),
                (
                    "legal",
                    models.BooleanField(
                        blank=True,
                        default=False,
                        verbose_name="implications légales (RGPD, AIPD..)",
                    ),
                ),
                (
                    "payload",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        verbose_name="contenu supplémentaire (JSON)",
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
                    ),
                    models.Index(fields=["level"], name="logs_action_level_04e687_idx"),
                    models.Index(fields=["legal"], name="logs_action_legal_30c8fc_idx"),
                ],
            },
        ),
    ]
