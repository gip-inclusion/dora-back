# Generated by Django 3.2.11 on 2022-01-27 09:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0034_alter_service_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="service",
            name="is_suggestion",
            field=models.BooleanField(default=False),
        ),
    ]
