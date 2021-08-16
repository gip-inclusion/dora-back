# Generated by Django 3.2.5 on 2021-08-16 17:53

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0002_alter_service_forms"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="service",
            name="contact_url",
        ),
        migrations.AlterField(
            model_name="service",
            name="address1",
            field=models.CharField(max_length=255, verbose_name="Adresse"),
        ),
        migrations.AlterField(
            model_name="service",
            name="beneficiaries_access_modes",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(
                    choices=[
                        ("OS", "Se présenter"),
                        ("PH", "Téléphoner"),
                        ("EM", "Envoyer un mail"),
                        ("OT", "Autre (préciser)"),
                    ],
                    max_length=2,
                ),
                size=None,
                verbose_name="Comment mobiliser la solution en tant que bénéficiaire",
            ),
        ),
        migrations.AlterField(
            model_name="service",
            name="categories",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(
                    choices=[
                        ("MO", "Mobilité"),
                        ("HO", "Logement"),
                        ("CC", "Garde d’enfant"),
                    ],
                    max_length=2,
                ),
                db_index=True,
                size=None,
                verbose_name="Catégorie principale",
            ),
        ),
        migrations.AlterField(
            model_name="service",
            name="city",
            field=models.CharField(max_length=200, verbose_name="Ville"),
        ),
        migrations.AlterField(
            model_name="service",
            name="coach_orientation_modes",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(
                    choices=[
                        ("PH", "Téléphoner"),
                        ("EM", "Envoyer un mail"),
                        ("EP", "Envoyer un mail avec une fiche de prescription"),
                        ("OT", "Autre (préciser)"),
                    ],
                    max_length=2,
                ),
                size=None,
                verbose_name="Comment orienter un bénéficiaire en tant qu’accompagnateur",
            ),
        ),
        migrations.AlterField(
            model_name="service",
            name="contact_email",
            field=models.EmailField(max_length=254, verbose_name="Courriel"),
        ),
        migrations.AlterField(
            model_name="service",
            name="contact_name",
            field=models.CharField(
                max_length=140, verbose_name="Nom du contact référent"
            ),
        ),
        migrations.AlterField(
            model_name="service",
            name="contact_phone",
            field=models.CharField(max_length=10, verbose_name="Numéro de téléphone"),
        ),
        migrations.AlterField(
            model_name="service",
            name="kinds",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(
                    choices=[
                        ("MA", "Aide materielle"),
                        ("FI", "Aide financière"),
                        ("SU", "Accompagnement"),
                    ],
                    max_length=2,
                ),
                db_index=True,
                size=None,
                verbose_name="Type de service",
            ),
        ),
        migrations.AlterField(
            model_name="service",
            name="location_kind",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(
                    choices=[("OS", "En présentiel"), ("RE", "À distance")],
                    max_length=2,
                ),
                size=None,
                verbose_name="Lieu de déroulement",
            ),
        ),
        migrations.AlterField(
            model_name="service",
            name="postal_code",
            field=models.CharField(max_length=5, verbose_name="Code postal"),
        ),
        migrations.AlterField(
            model_name="service",
            name="short_desc",
            field=models.TextField(max_length=280, verbose_name="Résumé"),
        ),
        migrations.AlterField(
            model_name="service",
            name="subcategories",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(
                    choices=[
                        ("MFH", "Aide aux frais de déplacements"),
                        ("MCR", "Réparation de voitures à prix réduit"),
                    ],
                    max_length=3,
                ),
                size=None,
                verbose_name="Sous-catégorie",
            ),
        ),
    ]
