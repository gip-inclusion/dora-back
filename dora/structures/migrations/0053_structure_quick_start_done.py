# Generated by Django 4.1.3 on 2023-03-16 15:11

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("structures", "0052_add_some_national_labels"),
    ]

    operations = [
        migrations.AddField(
            model_name="structure",
            name="quick_start_done",
            field=models.BooleanField(default=False),
        ),
    ]
