# Generated by Django 3.2.11 on 2022-01-25 13:59

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("structures", "0032_auto_20220117_1757"),
    ]

    operations = [
        migrations.AlterField(
            model_name="structure",
            name="source",
            field=models.CharField(
                blank=True,
                choices=[
                    ("DORA", "Équipe DORA"),
                    ("ITOU", "Import ITOU"),
                    ("PORTEUR", "Porteur"),
                    ("PE", "API Référentiel Agence PE"),
                    ("BI", "Invitations en masse"),
                    ("COL", "Suggestion collaborative"),
                ],
                db_index=True,
                max_length=12,
            ),
        ),
    ]
