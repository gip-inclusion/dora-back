# Generated by Django 4.2.11 on 2024-03-29 10:22

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0026_user_discovery_method"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="discovery_method_other",
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                verbose_name="comment avez-vous connu DORA\u202f? (autre)",
            ),
        ),
    ]
