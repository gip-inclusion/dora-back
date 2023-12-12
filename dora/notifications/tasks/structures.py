from datetime import timedelta

from django.utils import timezone

from dora.notifications.enums import TaskType
from dora.notifications.models import Notification
from dora.structures.models import Structure

from .core import Task


class OrphanStructuresTask(Task):
    @classmethod
    def task_type(cls):
        return TaskType.ORPHAN_STRUCTURES

    @classmethod
    def candidates(cls):
        return Structure.objects.orphans()

    @classmethod
    def should_trigger(cls, notification: Notification) -> bool:
        now = timezone.now()

        # il y a plus concis, mais cette version est plus lisible :
        # une notification tout de suite, puis 3 notifications à 2 semaines d'intervalle
        match notification.counter:
            case 0:
                return notification.updated_at < now
            case 1:
                return notification.updated_at + timedelta(weeks=2) <= now
            case 2:
                return notification.updated_at + timedelta(weeks=4) <= now
            case 3:
                return notification.updated_at + timedelta(weeks=6) <= now
            case _:
                return False

    @classmethod
    def process(cls, notification: Notification):
        # remplacer par l'implémentation (envoi de mail dans ce cas)
        print(
            f"Envoi de l'email pour : {notification.owner_structure.email} ({notification.owner_structure})"
        )


Task.register(OrphanStructuresTask)
