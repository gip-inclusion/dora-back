from django.core.management.base import BaseCommand

from dora.structures.emails import send_orphan_structure_notification
from dora.structures.models import Structure


class Command(BaseCommand):
    help = "Envoyer une notification pour les structures orphelines (pas de membres)"

    def add_arguments(self, parser):
        parser.add_argument(
            "-n",
            "--wet-run",
            action="store_true",
            help="Cette commande n'accomplit aucune action par défaut, et ne montre que le nombre de structures concernées."
            " Utiliser --wet-run pour lancer l'intégralité de la commande.",
        )

    def handle(self, *args, **options):
        wet_run = options["wet_run"]

        if not wet_run:
            self.stdout.write(self.style.NOTICE("DRY-RUN"))
        else:
            self.stdout.write(self.style.WARNING("PRODUCTION RUN"))

        orphan_structures = Structure.objects.exclude(email="").filter(
            members=None, putative_membership=None
        )
        # FIXME : à retirer après la phase de test, ou on ciblera un public restreint ...
        orphan_structures = orphan_structures.order_by("?")[:1]

        self.stdout.write(f"{orphan_structures.count()} structures concernées")

        if wet_run:
            for structure in orphan_structures:
                send_orphan_structure_notification(structure)

        self.stdout.write("Terminé !")
