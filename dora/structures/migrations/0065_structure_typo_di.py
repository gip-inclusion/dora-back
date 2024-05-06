# Generated by Django 4.2.11 on 2024-03-23 13:42

from data_inclusion.schema import Typologie
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("structures", "0064_pe_to_ft_typo"),
    ]

    operations = [
        migrations.AddField(
            model_name="structure",
            name="typo_di",
            field=models.CharField(
                choices=[(t.value, t.label) for t in Typologie],
                default="",
                max_length=100,
            ),
        ),
    ]