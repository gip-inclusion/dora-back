# Generated by Django 3.2.5 on 2021-08-26 12:57

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0016_auto_20210826_1456"),
    ]

    operations = [
        migrations.AddField(
            model_name="service",
            name="is_draft",
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name="service",
            name="address1",
            field=models.CharField(blank=True, max_length=255, verbose_name="Adresse"),
        ),
        migrations.AlterField(
            model_name="service",
            name="category",
            field=models.CharField(
                blank=True,
                choices=[
                    ("MO", "Mobilité"),
                    ("HO", "Logement"),
                    ("CC", "Garde d’enfant"),
                ],
                db_index=True,
                max_length=2,
                verbose_name="Catégorie principale",
            ),
        ),
        migrations.AlterField(
            model_name="service",
            name="city",
            field=models.CharField(blank=True, max_length=200, verbose_name="Ville"),
        ),
        migrations.AlterField(
            model_name="service",
            name="coach_orientation_modes",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(
                    choices=[
                        ("PH", "Téléphoner"),
                        ("EM", "Envoyer un mail"),
                        ("FO", "Envoyer le formulaire d’adhésion"),
                        ("EP", "Envoyer un mail avec une fiche de prescription"),
                        ("OT", "Autre (préciser)"),
                    ],
                    max_length=2,
                ),
                blank=True,
                default=list,
                size=None,
                verbose_name="Comment orienter un bénéficiaire en tant qu’accompagnateur",
            ),
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
                blank=True,
                db_index=True,
                default=list,
                size=None,
                verbose_name="Type de service",
            ),
        ),
        migrations.AlterField(
            model_name="service",
            name="location_kinds",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(
                    choices=[("OS", "En présentiel"), ("RE", "À distance")],
                    max_length=2,
                ),
                blank=True,
                default=list,
                size=None,
                verbose_name="Lieu de déroulement",
            ),
        ),
        migrations.AlterField(
            model_name="service",
            name="postal_code",
            field=models.CharField(
                blank=True, max_length=5, verbose_name="Code postal"
            ),
        ),
        migrations.AlterField(
            model_name="service",
            name="short_desc",
            field=models.TextField(blank=True, max_length=280, verbose_name="Résumé"),
        ),
        migrations.AlterField(
            model_name="service",
            name="subcategories",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(
                    choices=[
                        ("MO-MO", "Quand on veut se déplacer"),
                        ("MO-WK", "Quand on reprend un emploi ou une formation"),
                        ("MO-LI", "Quand on veut passer son permis"),
                        ("MO-VE", "Quand on a son permis mais pas de véhicule"),
                        ("MO-MA", "Quand on doit entretenir son véhicule"),
                        ("HO-SH", "Hebergement de courte durée"),
                        ("HO-AC", "Accéder au logement"),
                        ("HO-KE", "Conserver son logement"),
                        ("CC-IN", "Information et accompagnement des parents"),
                        ("CC-TM", "Garde ponctuelle"),
                        ("CC-LG", "Garde pérenne"),
                        ("CC-EX", "Garde périscolaire"),
                    ],
                    max_length=6,
                ),
                blank=True,
                default=list,
                size=None,
                verbose_name="Sous-catégorie",
            ),
        ),
    ]
