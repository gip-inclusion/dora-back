# Generated by Django 4.2.7 on 2023-11-23 10:26

from django.db import migrations


def add_new_categories(apps, schema_editor):
    ServiceCategory = apps.get_model("services", "ServiceCategory")
    ServiceSubCategory = apps.get_model("services", "ServiceSubCategory")

    ServiceCategory.objects.get_or_create(
        value="se-former", label="Préparer sa formation"
    )
    ServiceSubCategory.objects.get_or_create(
        value="se-former--monter-son-dossier-de-formation",
        label="Monter son dossier de formation",
    )
    ServiceSubCategory.objects.get_or_create(
        value="se-former--trouver-sa-formation",
        label="Trouver sa formation",
    )
    ServiceSubCategory.objects.get_or_create(
        value="se-former--utiliser-le-numerique",
        label="Utiliser le numérique",
    )

    ServiceCategory.objects.get_or_create(
        value="souvrir-a-linternational", label="S’ouvrir à l’international"
    )
    ServiceSubCategory.objects.get_or_create(
        value="souvrir-a-linternational--connaitre-les-opportunites-demploi-a-letranger",
        label="Connaître les opportunités d’emploi à l’étranger",
    )
    ServiceSubCategory.objects.get_or_create(
        value="souvrir-a-linternational--sinformer-sur-les-aides-pour-travailler-a-letranger",
        label="S’informer sur les aides pour travailler à l’étranger",
    )
    ServiceSubCategory.objects.get_or_create(
        value="souvrir-a-linternational--sorganiser-suite-a-son-retour-en-france",
        label="S’organiser suite à son retour en France",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0097_remove_bookmark_services_unique_bookmark_and_more"),
    ]

    operations = [
        migrations.RunPython(
            add_new_categories, reverse_code=migrations.RunPython.noop
        ),
    ]
