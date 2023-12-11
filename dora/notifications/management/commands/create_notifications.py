from django.core.management.base import BaseCommand

from dora.notifications.models import Notification
from dora.notifications.tasks import OrphanStructuresTask

"""
Création des tâches de notification:
    On place dans cette MC toutes les types notifications à créer,
    On lance une fois par jour (le soir ?)
"""


class Command(BaseCommand):
    help = "Création des tâches de notification"

    def add_arguments(self, parser):
        parser.add_argument(
            "--wet-run",
            action="store_true",
            help="Par défaut les taches sont seulement listées, pas executées. Ce paramètre active le traitement effectif des tâches.",
        )
        parser.add_argument(
            "--limit", type=int, help="Limite du nombre de tâches à traiter"
        )

    def handle(self, *args, **options):
        wet_run = options["wet_run"]
        limit = options["limit"]

        self.stdout.write("Creation des notifications")

        if wet_run:
            self.stdout.write(self.style.WARNING("PRODUCTION RUN"))
        else:
            self.stdout.write(self.style.NOTICE("DRY-RUN"))

        self.stdout.write("- Structures orphelines :")
        if notifications := OrphanStructuresTask.create_notifications(limit=limit):
            if wet_run:
                Notification.objects.bulk_create(notifications)
            self.stdout.write(f"{len(notifications)} enregistrements créés")

        # ajouter les autres types de notifications
        ...

        self.stdout.write("Terminé!")
