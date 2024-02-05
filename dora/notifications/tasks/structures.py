from datetime import timedelta

from django.utils import timezone

from dora.notifications.enums import TaskType
from dora.notifications.models import Notification
from dora.structures.emails import send_orphan_structure_notification
from dora.structures.models import Structure

from .core import Task, TaskError


class OrphanStructuresTask(Task):
    @classmethod
    def task_type(cls):
        return TaskType.ORPHAN_STRUCTURES

    @classmethod
    def candidates(cls):
        return Structure.objects.orphans().exclude(email="")

    @classmethod
    def should_trigger(cls, notification: Notification) -> bool:
        now = timezone.now()

        # il y a plus concis, mais cette version est plus lisible :
        # une notification tout de suite, puis 3 notifications à 2 semaines d'intervalle
        match notification.counter:
            case 0:
                return notification.created_at < now
            case 1:
                return notification.created_at + timedelta(weeks=2) <= now
            case 2:
                return notification.created_at + timedelta(weeks=4) <= now
            case 3:
                return notification.created_at + timedelta(weeks=6) <= now
            case _:
                return False

    @classmethod
    def process(cls, notification: Notification):
        try:
            send_orphan_structure_notification(notification.owner_structure)
        except Exception as ex:
            raise TaskError(f"Erreur d'envoi du mail ({notification}) : {ex}") from ex
        else:
            if notification.counter == 3:
                # cloturée au bout de 4 envois
                notification.complete()


Task.register(OrphanStructuresTask)
