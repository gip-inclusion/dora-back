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

        # FIXME:
        # si on inclut directement la valeur de `possible_tasks` dans la f-string ci-dessous,
        # ruff formattera le fichier au format python 3.12 (menant à une erreur sur python 3.11)
        # impossible de forcer un formattage compatible python 3.11 à cette heure (même avec `target-version`)
        # cause : voir https://docs.python.org/3/whatsnew/3.12.html#pep-701-syntactic-formalization-of-f-strings
        possible_tasks = "|".join(
            [task.task_type() for task in Task.registered_tasks()]
        )

        parser.add_argument(
            "--types",
            type=str,
            help=(
                f"Types de tâche de notification à prendre en compte, séparés par ','"
                f" ({possible_tasks})"
            ),
        )

    def handle(self, *args, **options):
        wet_run = options["wet_run"]
        limit = options["limit"]
        types = options["types"]

        self.stdout.write(self.help + " :")

        if wet_run:
            self.stdout.write(self.style.WARNING("PRODUCTION RUN\n"))
        else:
            self.stdout.write(self.style.NOTICE("DRY-RUN"))
            self.stdout.write(
                self.style.WARNING(
                    "Les notifications ne sont pas créées dans ce mode\n"
                )
            )

        if not Task.registered_tasks():
            self.stdout.write(" > aucune tâche enregistrée !")
            return

        # Par défaut, tous les types de tâches enregistrés sont sélectionnés
        selected_types = Task.registered_tasks()

        if types:
            selected_types = [
                task
                for task in Task.registered_tasks()
                if task.task_type() in types.split(",")
            ]

        if not selected_types:
            self.stdout.write(
                self.style.WARNING(
                    "Aucun type de tâche de notification sélectionné : fin du traitement"
                )
            )
            return

        total_timer = 0

        for task_class in selected_types:
            task = task_class()

            self.stdout.write(
                self.style.NOTICE(
                    f"> {task_class.__name__} ({task_class.task_type()}) :"
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    f" > nombre d'éléments candidats : {len(task.candidates())}"
                )
            )

            timer = time.time()
            ok, errors, obsolete = task.run(
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
