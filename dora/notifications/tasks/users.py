from dateutil.relativedelta import relativedelta
from django.utils import timezone

from dora.notifications.enums import TaskType
from dora.notifications.models import Notification
from dora.users.emails import send_user_without_structure_notification
from dora.users.models import User

from .core import Task, TaskError

"""
Users :
    Notifications ayant pour candidats des utilisateurs "en direct",
    c.a.d. sans passer par l'intermédiaire d'un objet tiers,
    comme une invitation ou une structure.
"""


class UsersWithoutStructureTask(Task):
    @classmethod
    def task_type(cls):
        return TaskType.USERS_WITHOUT_STRUCTURE

    @classmethod
    def candidates(cls):
        return User.objects.exclude(ic_id=None).filter(
            is_valid=True,
            membership=None,
            putative_membership=None,
            date_joined__gt=timezone.now() - relativedelta(months=4, days=1),
        )

    @classmethod
    def should_trigger(cls, notification: Notification) -> bool:
        now = timezone.now()
        match notification.counter:
            case 0:
                return notification.created_at + relativedelta(days=1) <= now
            case 1:
                return notification.created_at + relativedelta(days=5) <= now
            case 2:
                return notification.created_at + relativedelta(days=10) <= now
            case 3:
                return notification.created_at + relativedelta(days=15) <= now
            case 4:
                return notification.created_at + relativedelta(months=4) <= now
            case _:
                return False

    @classmethod
    def process(cls, notification: Notification):
        match notification.counter:
            case 0 | 1 | 2 | 3:
                try:
                    send_user_without_structure_notification(
                        notification.owner_user, deletion=notification.counter == 3
                    )
                except Exception as ex:
                    raise TaskError(
                        f"Erreur d'envoi du mail pour un utilisateur sans structure ({notification}) : {ex}"
                    ) from ex
            case 4:
                notification.complete()
                # action : voir post_process
            case _:
                raise TaskError(f"État du compteur incohérent ({notification})")

    @classmethod
    def post_process(cls, notification: Notification):
        print("PP")
        if notification.is_complete:
            print("PP:deleting")
            user = notification.owner_user
            # suppression du compte utilisateur associé si :
            # - aucune autre invitation
            # - non membre d'une structure
            if not user.putative_membership.count() and not user.membership.count():
                user.delete()
                # à ce point, la notification doit aussi être détruite (CASCADE)...


Task.register(UsersWithoutStructureTask)
