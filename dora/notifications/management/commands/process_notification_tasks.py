from django.core.management.base import BaseCommand

from dora.notifications.tasks.core import Task

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

        if not Task.registered():
            self.stdout.write(" > aucune tâche enregistrée!")
            return

        for task_class in Task.registered():
            self.stdout.write(f"> {task_class.__name__} :")

            ok, errors, obsolete = task_class().run(
                strict=True, dry_run=not wet_run, limit=limit
            )

            if ok:
                self.stdout.write(f"{ok} notification(s) traitée(s)")
            else:
                self.stdout.write(" > aucune notification traitée")

            if errors:
                self.stdout.write(f" > {errors} notification(s) en erreur")
            else:
                self.stdout.write(" > aucune erreur")

            if obsolete:
                self.stdout.write(f" > {obsolete} notification(s) obsolètes modifiées")
            else:
                self.stdout.write(" > aucune notification obsolète")

        self.stdout.write("Terminé!")

    # TODO : timers
