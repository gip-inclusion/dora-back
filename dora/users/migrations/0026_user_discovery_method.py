# Generated by Django 4.2.11 on 2024-03-28 17:01

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0025_remove_user_department"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="discovery_method",
            field=models.CharField(
                blank=True,
                choices=[
                    (
                        "bouche-a-oreille",
                        "Bouche-à-oreille (mes collègues, réseau, etc.)",
                    ),
                    (
                        "moteurs-de-recherche",
                        "Moteurs de recherche (Ecosia, Qwant, Google, Bing, etc.)",
                    ),
                    ("reseaux-sociaux", "Réseaux sociaux (Linkedin, Twitter, etc.)"),
                    (
                        "evenements-dora",
                        "Événements DORA (démonstration, webinaires, open labs, etc.)",
                    ),
                    ("autre", "Autre (préciser)"),
                ],
                max_length=25,
                null=True,
                verbose_name="comment avez-vous connu DORA\u202f?",
            ),
        ),
    ]
