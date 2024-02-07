from dateutil.relativedelta import relativedelta
from django.utils import timezone

from dora.notifications.enums import TaskType
from dora.notifications.models import Notification
from dora.structures.emails import (
    send_admin_invited_users_20_notification,
    send_admin_invited_users_90_notification,
)
from dora.structures.models import StructurePutativeMember
from dora.users.emails import send_invitation_reminder

from .core import Task, TaskError


class InvitedUsersTask(Task):
    @classmethod
    def task_type(cls):
        return TaskType.INVITED_USERS

    @classmethod
    def candidates(cls):
        # en CAT 1 : depuis 6 mois ou +
        # - invitations à une structure en attente
        # - pour les utilisateurs invité par un admin
        # - mais qui n'ont pas validé leur e-mail
        return StructurePutativeMember.objects.filter(
            invited_by_admin=True,
            user__is_valid=False,
            creation_date__gt=timezone.now() - relativedelta(months=6),
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
                return notification.created_at + relativedelta(days=20) <= now
            case 5:
                return notification.created_at + relativedelta(days=90) <= now
            case 6:
                return notification.created_at + relativedelta(days=120) <= now
            case _:
                return False

    @classmethod
    def process(cls, notification: Notification):
        # plusieurs actions et "cibles" en fonction du temps écoulé
        match notification.counter:
            case 0 | 1 | 2 | 3:
                # relance pour les utilisateurs
                try:
                    send_invitation_reminder(
                        notification.owner_structureputativemember.user,
                        notification.owner_structureputativemember.structure,
                    )
                except Exception as ex:
                    raise TaskError(
                        f"Erreur d'envoi de la relance d'invitation ({notification}): {
                            ex}"
                    ) from ex
            case 4:
                # notifications aux administrateurs 20j
                try:
                    send_admin_invited_users_20_notification(
                        notification.owner_structureputativemember.structure,
                        notification.owner_structureputativemember.user,
                    )
                except Exception as ex:
                    raise TaskError(
                        f"Erreur d'envoi de la relance (1) aux administrateurs ({
                            notification}): {ex}"
                    ) from ex
            case 5:
                # notifications aux administrateurs 90j
                try:
                    send_admin_invited_users_90_notification(
                        notification.owner_structureputativemember.structure,
                        notification.owner_structureputativemember.user,
                    )
                except Exception as ex:
                    raise TaskError(
                        f"Erreur d'envoi de la relance (2) aux administrateurs ({
                            notification}): {ex}"
                    ) from ex
            case 6:
                # clôture au préalable de la notification
                notification.complete()

                # action : voir post_process()
            case _:
                raise TaskError(f"Incohérence de compteur ({notification})")

    @classmethod
    def post_process(cls, notification: Notification):
        # cette partie est en "post-process", puisque l'on va détruire le propriétaire de la notification
        # si on effectue cette partie pendant le traitement des tâches,
        # le traitement va planter puisque la notification n'existe plus (détruite en CASCADE).
        if notification.is_complete:
            user = notification.owner_structureputativemember.user

            # suppression de l'invitation :
            notification.owner_structureputativemember.delete()
            # à ce point, la notification doit aussi être détruite (CASCADE)...

            # suppression du compte utilisateur associé si :
            # - aucune autre invitation
            # - non membre d'une structure
            if not user.putative_membership.count() and not user.membership.count():
                user.delete()


Task.register(InvitedUsersTask)
