# Generated by Django 4.0.4 on 2022-07-07 13:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0056_servicemodel_alter_service_model"),
    ]

    operations = [
        migrations.AddField(
            model_name="service",
            name="filling_duration",
            field=models.IntegerField(default=0),
        ),
    ]
