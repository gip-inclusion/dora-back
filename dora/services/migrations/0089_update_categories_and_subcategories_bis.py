# Generated by Django 4.0.6 on 2022-08-17 12:57

from django.db import migrations

from dora.services.migration_utils import update_category_value_and_label


def migrate_services_options(apps, schema_editor):
    ServiceCategory = apps.get_model("services", "ServiceCategory")
    ServiceSubCategory = apps.get_model("services", "ServiceSubCategory")

    # Liste des modifications
    #   - emploi-trouver-emploi => trouver-un-emploi
    #   - emploi-choisir-metier => choisir-un-metier
    #   - emploi-preparer-sa-candidature => preparer-sa-candidature
    #   - acces-aux-droits => acces-aux-droits-et-citoyennete
    #   - equipement-alimentation => equipement-et-alimentation

    update_category_value_and_label(
        ServiceCategory,
        ServiceSubCategory,
        "equipement-alimentation",
        "equipement-et-alimentation",
        "Équipement et alimentation",
    )
    update_category_value_and_label(
        ServiceCategory,
        ServiceSubCategory,
        "acces-aux-droits",
        "acces-aux-droits-et-citoyennete",
        "Accès aux droits & citoyenneté",
    )
    update_category_value_and_label(
        ServiceCategory,
        ServiceSubCategory,
        "emploi-choisir-metier",
        "choisir-un-metier",
        "Emploi - Choisir un métier",
    )
    update_category_value_and_label(
        ServiceCategory,
        ServiceSubCategory,
        "emploi-preparer-sa-candidature",
        "preparer-sa-candidature",
        "Emploi - Préparer sa candidature",
    )
    update_category_value_and_label(
        ServiceCategory,
        ServiceSubCategory,
        "emploi-trouver-emploi",
        "trouver-un-emploi",
        "Emploi - Trouver un emploi",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0088_update_categories_and_subcategories_bis"),
    ]

    operations = [
        migrations.RunPython(
            migrate_services_options, reverse_code=migrations.RunPython.noop
        ),
    ]
