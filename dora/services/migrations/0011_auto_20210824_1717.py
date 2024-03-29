# Generated by Django 3.2.5 on 2021-08-24 15:17

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0010_alter_service_subcategories"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="service",
            name="categories",
        ),
        migrations.AddField(
            model_name="service",
            name="category",
            field=models.CharField(
                choices=[
                    ("MO", "Mobilité"),
                    ("HO", "Logement"),
                    ("CC", "Garde d’enfant"),
                ],
                db_index=True,
                default="MO",
                max_length=2,
                verbose_name="Catégorie principale",
            ),
        ),
    ]
