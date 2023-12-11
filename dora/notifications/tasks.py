from datetime import timedelta

from django.utils import timezone

from dora.structures.models import Structure

from .enums import TaskType
from .models import Notification, Task

"""
Tasks:
    Création des jeux de notifications pour chaque type.
    Il s'agit de la planification proprement dites.
    Le jeu de notification n'est pas sauvegardé en base.
    (bulk_create ou simple save si une seule structure sont à faire).

    Ici en exemple, les structures orphelines.
    Sur une copie de la base de production, en local, la création en `bulk_create`
    prends quelques secondes pour 5k+ structures orphelines.
"""


class OrphanStructuresTask(Task):
    @classmethod
    def type(cls):
        return TaskType.ORPHAN_STRUCTURES

    @classmethod
    def create_notifications(cls, limit=0):
        """Crée un jeu de notification de rappel pour une ou plusieurs structures orphelines."""
        already_created = (
            Notification.objects.filter(task_type=TaskType.ORPHAN_STRUCTURES)
            .values_list("owner_structure_id", flat=True)
            .distinct()
        )

        if orphan_structures := (
            Structure.objects.filter(membership=None, putative_membership=None)
            .exclude(email="")
            .exclude(pk__in=list(already_created))
        ):
            if limit:
                orphan_structures = orphan_structures[:limit]

            result = []
            now = timezone.now()

            for structure in orphan_structures:
                kwargs = {
                    "task_type": TaskType.ORPHAN_STRUCTURES,
                    "owner_structure": structure,
                }
                # une relance tous les 15j / deux semaines x 4
                result.append(Notification(triggers_at=now, **kwargs))
                result.append(
                    Notification(triggers_at=now + timedelta(weeks=2), **kwargs)
                )
                result.append(
                    Notification(triggers_at=now + timedelta(weeks=4), **kwargs)
                )
                result.append(
                    Notification(triggers_at=now + timedelta(weeks=6), **kwargs)
                )
                result.append(
                    Notification(triggers_at=now + timedelta(weeks=8), **kwargs)
                )

            return result

        return []

    @classmethod
    def run(cls, notification: Notification):
        super().run(notification)
        # send email
        print(
            f"Envoi de l'email pour : {notification.owner_structure.email} ({notification.owner_structure})"
        )
