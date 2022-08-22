# Generated by Django 4.0.6 on 2022-08-17 10:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("structures", "0044_add_pe_structure_source"),
    ]

    operations = [
        migrations.AddField(
            model_name="structure",
            name="moderation_date",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="structure",
            name="moderation_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("NEED_INITIAL_MODERATION", "Première modération nécessaire"),
                    ("NEED_NEW_MODERATION", "Nouvelle modération nécessaire"),
                    ("IN_PROGRESS", "En cours"),
                    ("VALIDATED", "Validé"),
                ],
                db_index=True,
                max_length=30,
                null=True,
                verbose_name="Modération",
            ),
        ),
        migrations.AlterField(
            model_name="structure",
            name="modification_date",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
