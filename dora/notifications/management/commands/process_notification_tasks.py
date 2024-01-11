import time

from django.core.management.base import BaseCommand

from dora.notifications.tasks.core import Task

"""
Lancement / activation des notifications :
    - récupère la liste des tâches actuellement enregitrées
    - effectue un `run()` sur chaque tâche (rafraichissement, purge, et actions)

Limite d'enregistrement à traiter possible et dry-run par défaut.

La planification de cette commande reste à définir (1x/j a priori).
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

        self.stdout.write(self.help + " :")

        if wet_run:
            self.stdout.write(self.style.WARNING("PRODUCTION RUN"))
        else:
            self.stdout.write(self.style.NOTICE("DRY-RUN"))
            self.stdout.write("Les notifications ne sont pas créées dans ce mode")

        if not Task.registered_tasks():
            self.stdout.write(" > aucune tâche enregistrée!")
            return

        total_timer = 0

        for task_class in Task.registered_tasks():
            self.stdout.write(self.style.NOTICE(f"> {task_class.__name__} :"))

            timer = time.time()
            ok, errors, obsolete = task_class().run(
                strict=True, dry_run=not wet_run, limit=limit
            )
            timer = time.time() - timer

            if ok:
                self.stdout.write(
                    self.style.SUCCESS(
                        f" > {ok} notification(s) traitée(s) en {timer:.2f}s"
                    )
                )
                total_timer += timer
            else:
                self.stdout.write(" > aucune notification traitée")

            if errors:
                self.stdout.write(
                    self.style.ERROR(f" > {errors} notification(s) en erreur")
                )
            else:
                self.stdout.write(" > aucune erreur")

            if obsolete:
                self.stdout.write(
                    self.style.SUCCESS(
                        f" > {obsolete} notification(s) obsolètes modifiées"
                    )
                )
            else:
                self.stdout.write(" > aucune notification obsolète")

        self.stdout.write(self.style.NOTICE(f"Terminé en {total_timer:.2f}s !"))
