from dateutil.relativedelta import relativedelta
from django.utils import timezone

from dora.notifications.enums import TaskType
from dora.notifications.models import Notification
from dora.users.emails import send_account_deletion_notification
from dora.users.models import User

from .core import Task, TaskError

"""
Users :
    Notifications ayant pour candidats des utilisateurs "en direct",
    c.a.d. sans passer par l'intermédiaire d'un objet tiers,
    comme une invitation ou une structure.
"""


class UserAccountDeletionTask(Task):
    @classmethod
    def task_type(cls):
        return TaskType.USER_ACCOUNT_DELETION

    @classmethod
    def candidates(cls):
        # CAT 5 :
        # les utilisateurs "actifs" qui ne se sont pas connecté depuis plus de 2 ans
        return User.objects.filter(
            is_active=True, last_login__lte=timezone.now() - relativedelta(years=2)
        )

    @classmethod
    def should_trigger(cls, notification: Notification) -> bool:
        now = timezone.now()

        match notification.counter:
            case 0:
                # on notifie immédiatement :
                return notification.created_at <= now
            case 1:
                return notification.created_at + relativedelta(days=30) <= now
            case _:
                return False

    @classmethod
    def process(cls, notification: Notification):
        match notification.counter:
            case 0:
                try:
                    send_account_deletion_notification(notification.owner_user)
                except Exception as ex:
                    raise TaskError(
                        f"Erreur à l'envoi de l'e-mail de suppression de compte ({notification})"
                    ) from ex
            case 1:
                # la notification se termine
                # pour l'action sur le propriétaire : voir `post_process`
                notification.complete()
            case _:
                raise TaskError(f"Incohérence de compteur ({notification})")

    @classmethod
    def post_process(cls, notification: Notification):
        if notification.is_complete:
            notification.owner_user.delete()
            # à ce point, la notification est détruite en cascade


Task.register(UserAccountDeletionTask)
