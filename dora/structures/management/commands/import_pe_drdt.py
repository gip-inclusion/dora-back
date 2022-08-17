import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.utils import IntegrityError

from dora.sirene.models import Establishment
from dora.structures.models import Structure, StructureSource, StructureTypology
from dora.users.models import User


class Command(BaseCommand):
    help = "Import les directions régionales et territoriales Pole"

    def handle(self, *args, **options):

        mapping_file_path = (
            Path(__file__).parent.parent.parent / "data" / "PE-DRDT-siret-safir.csv"
        )

        bot_user = User.objects.get_dora_bot()
        source = StructureSource.objects.get(value="dr-dt-pole-emploi")
        typology = StructureTypology.objects.get(value="PE")
        with open(mapping_file_path) as mapping_file:
            reader = csv.reader(mapping_file)

            next(reader)  # passe l'en-tête
            for row in reader:
                name, safir, siret = row[0], row[1].strip(), row[2].strip()
                try:
                    structure = Structure.objects.get(siret=siret)
                    self.stdout.write(
                        self.style.WARNING(
                            f"Structure already exists {name}: {structure.name}"
                        )
                    )
                except Structure.DoesNotExist:
                    try:
                        establishment = Establishment.objects.get(siret=siret)
                    except Establishment.DoesNotExist:
                        self.stdout.write(
                            self.style.ERROR(
                                f"No establishment for siret {siret} for {name}"
                            )
                        )
                        continue
                    with transaction.atomic(durable=True):
                        structure = Structure.objects.create_from_establishment(
                            establishment
                        )
                        # TODO: ajoute une notification de modération ?
                        structure.source = source
                        structure.creator = bot_user
                        structure.last_editor = bot_user
                        structure.code_safir_pe = safir
                        structure.last_editor = bot_user
                        structure.typology = typology
                        try:
                            with transaction.atomic():
                                structure.save()
                        except IntegrityError:
                            self.stdout.write(
                                self.style.ERROR(
                                    f"Safir code {safir} for {name} already in use in {Structure.objects.get(code_safir_pe=safir).name}"
                                )
                            )
                            continue
