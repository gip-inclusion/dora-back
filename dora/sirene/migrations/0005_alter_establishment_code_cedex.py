# Generated by Django 3.2.8 on 2021-11-23 18:03

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sirene", "0004_alter_establishment_code_cedex"),
    ]

    operations = [
        migrations.AlterField(
            model_name="establishment",
            name="code_cedex",
            field=models.CharField(max_length=5),
        ),
    ]
