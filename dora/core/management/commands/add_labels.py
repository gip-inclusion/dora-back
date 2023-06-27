import csv

from django.core.management.base import BaseCommand
from rest_framework import serializers

from dora.structures.models import Structure, StructureNationalLabel

#################
# Format du CSV attendu:
# | label | siret |


class ImportSerializer(serializers.Serializer):
    label = serializers.CharField()
    siret = serializers.CharField()

    def validate_label(self, label_value):
        return StructureNationalLabel.objects.get(value=label_value)

    def validate(self, data):
        raw_siret = data.get("siret")
        siret = "".join([c for c in raw_siret if c.isdigit()])
        if len(siret) != 14:
            raise serializers.ValidationError(f"Siret invalide: {raw_siret}")
        try:
            data["structure"] = Structure.objects.get(siret=siret)
        except Structure.DoesNotExist:
            raise serializers.ValidationError(f"Siret inconnu: {siret}")
        return super().validate(data)


class Command(BaseCommand):
    help = "Importe une liste de structures"

    def add_arguments(self, parser):
        parser.add_argument("filename")

    def handle(self, *args, **options):
        filename = options["filename"]
        with open(filename) as labels_file:
            labels = csv.reader(labels_file, delimiter=",")
            for i, row in enumerate(labels):
                f = ImportSerializer(data={"label": row[0], "siret": row[1]})

                if f.is_valid():
                    data = f.validated_data
                    structure = data["structure"]
                    label = data["label"]
                    print(
                        f"Ajout du label `{label.value}` à {structure.get_frontend_url()}",
                        end="",
                    )
                    if label not in structure.national_labels.all():
                        print(" (manquant)")
                        structure.national_labels.add(label)
                    else:
                        print(" (déjà présent)")

                else:
                    for field, errors in f.errors.items():
                        for error in errors:
                            self.stdout.write(self.style.ERROR(f"{str(error)}"))
