# Generated by Django 4.0.7 on 2022-09-13 15:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        (
            "structures",
            "0047_structurenationallabel_structure_accesslibre_url_and_more",
        ),
    ]

    def add_national_labels(apps, _):
        StructureNationalLabel = apps.get_model("structures", "StructureNationalLabel")
        StructureNationalLabel.objects.create(
            value="france-service", label="France service"
        )
        StructureNationalLabel.objects.create(value="caf", label="CAF")
        StructureNationalLabel.objects.create(value="pole-emploi", label="Pôle emploi")
        StructureNationalLabel.objects.create(value="french-tech", label="French Tech")
        StructureNationalLabel.objects.create(value="mobin", label="Mobin")
        StructureNationalLabel.objects.create(value="anlci", label="ANLCI")
        StructureNationalLabel.objects.create(value="unea", label="UNEA")

    operations = [
        migrations.RunPython(
            add_national_labels, reverse_code=migrations.RunPython.noop
        ),
    ]