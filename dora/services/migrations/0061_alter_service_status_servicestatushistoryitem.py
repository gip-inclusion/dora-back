# Generated by Django 4.0.6 on 2022-07-18 14:33

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("services", "0060_Cleanup"),
    ]

    operations = [
        migrations.AlterField(
            model_name="service",
            name="status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("SUGGESTION", "Suggestion"),
                    ("DRAFT", "Draft"),
                    ("PUBLISHED", "Published"),
                    ("ARCHIVED", "Archived"),
                ],
                db_index=True,
                max_length=20,
                null=True,
                verbose_name="Statut",
            ),
        ),
        migrations.CreateModel(
            name="ServiceStatusHistoryItem",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("date", models.DateTimeField(auto_now=True, db_index=True)),
                (
                    "new_status",
                    models.CharField(
                        choices=[
                            ("SUGGESTION", "Suggestion"),
                            ("DRAFT", "Draft"),
                            ("PUBLISHED", "Published"),
                            ("ARCHIVED", "Archived"),
                        ],
                        db_index=True,
                        max_length=20,
                        verbose_name="Nouveau statut",
                    ),
                ),
                (
                    "previous_status",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("SUGGESTION", "Suggestion"),
                            ("DRAFT", "Draft"),
                            ("PUBLISHED", "Published"),
                            ("ARCHIVED", "Archived"),
                        ],
                        max_length=20,
                        null=True,
                        verbose_name="Statut précédent",
                    ),
                ),
                (
                    "service",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="status_history_item",
                        to="services.service",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Historique des statuts de service",
                "ordering": ["-date"],
                "get_latest_by": "date",
            },
        ),
    ]
