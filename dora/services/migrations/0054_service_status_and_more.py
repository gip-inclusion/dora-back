# Generated by Django 4.0.4 on 2022-06-16 14:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0053_alter_servicemodificationhistoryitem_service"),
    ]

    operations = [
        migrations.AddField(
            model_name="service",
            name="status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("SUGGESTION", "Suggestion"),
                    ("DRAFT", "Draft"),
                    ("PUBLISHED", "Published"),
                    ("UNPUBLISHED", "Unpublished"),
                    ("ARCHIVED", "Archived"),
                ],
                db_index=True,
                max_length=20,
                null=True,
                verbose_name="Statut",
            ),
        ),
        migrations.AddConstraint(
            model_name="service",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("is_model", False), ("status__isnull", True), _connector="OR"
                ),
                name="services_service_status_not_empty_except_models",
            ),
        ),
    ]
