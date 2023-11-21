from django.core.management.base import BaseCommand

from dora.core.constants import SIREN_POLE_EMPLOI
from dora.structures.models import Structure


class Command(BaseCommand):
    help = "Supprime les structures Pôle emploi qui n’ont ni collaborateurs ni services"

    def handle(self, *args, **options):
        pe_structures = Structure.objects.filter(siret__startswith=SIREN_POLE_EMPLOI)
        cleanable_structs = pe_structures.filter(
            membership__isnull=True,
            putative_membership__isnull=True,
            services__isnull=True,
        )
        self.stdout.write(
            f"Suppression de {cleanable_structs.count()} structures inutilisées"
        )
        cleanable_structs.delete()
