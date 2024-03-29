# Generated by Django 4.0.6 on 2022-07-20 14:02

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0061_alter_service_status_servicestatushistoryitem"),
    ]

    operations = [
        migrations.AddField(
            model_name="servicemodificationhistoryitem",
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
                default="",
                max_length=20,
                verbose_name="Statut après modification",
            ),
        ),
    ]
