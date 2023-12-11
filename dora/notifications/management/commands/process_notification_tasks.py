from django.core.management.base import BaseCommand

from dora.notifications.enums import TaskType
from dora.notifications.models import Notification
from dora.notifications.tasks import OrphanStructuresTask

"""
Lancement / activation des notifications :
    Contrairement à la création, lancement à intervalle régulier dans la journée (2h?),
    si il y a une granularité de planification inférieure au jour.
"""


class Command(BaseCommand):
    help = "Lancement des tâches de notification"

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

        if wet_run:
            self.stdout.write(self.style.WARNING("PRODUCTION RUN"))
        else:
            self.stdout.write(self.style.NOTICE("DRY-RUN"))

        self.stdout.write("Envoi des notifications")

        if notifications_pendings := Notification.objects.pending().should_trigger():
            if limit:
                notifications_pendings = notifications_pendings[:limit]

            for notification in notifications_pendings:
                if not wet_run:
                    continue
                match notification.task_type:
                    case TaskType.ORPHAN_STRUCTURES:
                        try:
                            # par ex. appeler l'envoi d'email avec la structure contenue dans la tache
                            OrphanStructuresTask.run(notification)
                        except Exception:
                            # log me
                            pass
                        else:
                            # en fin de tache:
                            notification.complete()

                    case _:
                        pass
            self.stdout.write(f"{len(notifications_pendings)} notifications traitées")

        self.stdout.write("Terminé!")

    # TODO : timers
