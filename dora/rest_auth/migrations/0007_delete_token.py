# Generated by Django 4.2.10 on 2024-03-19 10:54

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("rest_auth", "0006_switch_to_drf_tokens"),
    ]

    operations = [
        migrations.DeleteModel(
            name="Token",
        ),
    ]
