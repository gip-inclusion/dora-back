# Generated by Django 3.2.5 on 2021-09-18 09:41

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sirene", "0002_alter_establishment_code_commune"),
    ]

    operations = [
        migrations.AddField(
            model_name="establishment",
            name="is_social",
            field=models.BooleanField(default=False),
            preserve_default=False,
        ),
    ]
