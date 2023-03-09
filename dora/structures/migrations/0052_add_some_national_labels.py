# Generated by Django 4.0.7 on 2022-09-13 15:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        (
            "structures",
            "0051_alter_structurenationallabel_options_and_more",
        ),
    ]

    def add_national_labels(apps, _):
        StructureNationalLabel = apps.get_model("structures", "StructureNationalLabel")

        # Ajout de Collectif Emploi
        StructureNationalLabel.objects.get_or_create(
            value="collectif-emploi", label="Collectif emploi"
        )

        # Mise à jour de CAP emploi
        cap_emploi = StructureNationalLabel.objects.filter(value="cheops").first()
        if cap_emploi:
            cap_emploi.value = "cap-emploi-cheops"
            cap_emploi.label = "CAP Emploi - Réseau CHEOPS"
            cap_emploi.save()

    operations = [
        migrations.RunPython(
            add_national_labels, reverse_code=migrations.RunPython.noop
        ),
    ]
