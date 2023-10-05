# Generated by Django 4.2.3 on 2023-10-05 09:25

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("services", "0095_remove_service_is_draft_remove_service_is_suggestion"),
    ]

    operations = [
        migrations.CreateModel(
            name="DiBookmark",
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
                ("di_id", models.CharField(max_length=50)),
                (
                    "creation_date",
                    models.DateTimeField(auto_now_add=True, db_index=True),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="dibookmark",
            constraint=models.UniqueConstraint(
                fields=("di_id", "user"), name="services_unique_di_bookmark"
            ),
        ),
    ]
