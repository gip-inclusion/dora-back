import uuid
from abc import ABCMeta, abstractclassmethod

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from dora.structures.models import Structure

from .enums import NotificationStatus, TaskType


class NotificationError(Exception):
    pass


class Task(metaclass=ABCMeta):
    """
    Deux parties :
        - création, sans enregistrement des notifications
        - execution de la tâche
    """

    @abstractclassmethod
    def type(cls) -> TaskType:
        pass

    @abstractclassmethod
    def create_notifications(cls, limit=0) -> list:
        pass

    @abstractclassmethod
    def run(cls, notification):
        if notification.task_type != cls.type():
            raise NotificationError(
                f"Type de notification incompatible : {notification.task_type}"
            )


class NotificationQueryset(models.QuerySet):
    # à deplacer vers la structure (dans le manager ou un queryset)
    # def orphans(self):
    #     return self.filter(membership=None, putative_membership=None).exclude(email="")

    def for_structure(self, structure):
        return self.filter(structure=structure)

    def should_trigger(self):
        return self.pending().filter(triggers_at__lte=timezone.now())

    def pending(self):
        return self.filter(status=NotificationStatus.PENDING)

    def processed(self):
        return self.filter(status=NotificationStatus.PROCESSED)

    def expired(self):
        return self.filter(status=NotificationStatus.EXPIRED)


class Notification(models.Model):
    """
    Exemple de notification / tâche liée à un objet métier.
    Pour cette exemple, uniquement les structures.
    """

    # TODO: verbose_name

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.IntegerField(
        choices=NotificationStatus.choices, default=NotificationStatus.PENDING
    )

    task_type = models.CharField(choices=TaskType.choices)
    triggers_at = models.DateTimeField()
    expires_at = models.DateTimeField(null=True, blank=True)

    # Propriétaires potentiels
    owner_structure = models.ForeignKey(
        Structure, null=True, blank=True, on_delete=models.CASCADE
    )
    ...

    objects = NotificationQueryset.as_manager()

    class Meta:
        # ajouter des contraintes pour chaque type de propriètaire possible
        constraints = [
            models.CheckConstraint(
                name="check_structure", check=~models.Q(owner_structure=None)
            ),
            # ajouter une contrainte pour chaque type
        ]
        indexes = [
            models.Index(fields=("task_type",)),
            models.Index(fields=("status",)),
            models.Index(fields=("triggers_at",)),
        ]

    def clean(self):
        match self.task_type:
            case TaskType.ORPHAN_STRUCTURES:
                if not self.owner_structure_id:
                    raise ValidationError("Aucune structure attachée")
                ...
            case _:
                raise ValidationError("Type de notification inconnu")

    def complete(self):
        self.full_clean()
        self.updated_at = timezone.now()
        self.status = NotificationStatus.PROCESSED
        self.save()

    @property
    def owner(self):
        if self.owner_structure_id:
            return self.owner_structure

        # ajouter autant de modèles que de propriétaire possible
        ...

        # ne devrait pas être possible avec la contrainte,
        # sauf si la notification n'est oas sauvegardée
        raise NotificationError("Aucun propriétaire défini pour la notification")

    @property
    def expired(self):
        return self.expires_at and self.expires_at < timezone.now()

    @property
    def should_trigger(self):
        return (
            not self.expired
            and self.status == NotificationStatus.PENDING
            and self.triggers_at <= timezone.now()
        )
