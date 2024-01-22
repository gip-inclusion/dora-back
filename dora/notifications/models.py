import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from dora.structures.models import Structure

from .enums import NotificationStatus, TaskType


class NotificationError(Exception):
    pass


class NotificationQueryset(models.QuerySet):
    def pending(self):
        return self.filter(status=NotificationStatus.PENDING)

    def complete(self):
        return self.filter(status=NotificationStatus.COMPLETE)

    def expired(self):
        return self.filter(status=NotificationStatus.EXPIRED)


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Date de création"
    )
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name="Date de modification"
    )
    status = models.CharField(
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
        verbose_name="Statut",
    )

    task_type = models.CharField(choices=TaskType.choices, verbose_name="Type de tâche")
    counter = models.IntegerField(default=0, verbose_name="Compteur d'exécution")
    expires_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Date d'expiration"
    )

    # propriétaires potentiels :
    # chaque type de propriétaire de notification doit avoir :
    # - une définition de FK associée au modèle de notification
    # - nommée `owner_nom_du_modele_cible` (important)
    owner_structure = models.ForeignKey(
        Structure,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name="Structure propriétaire",
    )
    ...

    objects = NotificationQueryset.as_manager()

    def __str__(self):
        return f"ID:{self.pk}, TASK_TYPE:{self.task_type}, STATUS:{self.status}"

    class Meta:
        # ajouter des contraintes pour chaque type de propriètaire possible
        constraints = [
            models.CheckConstraint(
                name="check_structure",
                check=~models.Q(owner_structure=None),
                # | ~models.Q(owner_other_model=None) ...
                # ajouter une contrainte pour chaque type de propriétaire
            ),
        ]
        indexes = [
            models.Index(fields=("task_type",)),
            models.Index(fields=("status",)),
            models.Index(fields=("updated_at",)),
        ]
        # par définition, une seule définition par propriétaire pour un type de táche donné
        unique_together = [("task_type", "owner_structure_id")]

    def clean(self):
        # essentiellement pour vérification de la présence des FK,
        # mais peut être agrementé
        match self.task_type:
            case TaskType.ORPHAN_STRUCTURES:
                if not self.owner_structure_id:
                    raise ValidationError("Aucune structure attachée")
                ...

        if self.task_type not in TaskType.values:
            raise ValidationError("Type de notification inconnu")

    def trigger(self):
        self.full_clean()
        self.updated_at = timezone.now()
        self.counter += 1
        self.save()

    def complete(self):
        if self.status in (NotificationStatus.COMPLETE, NotificationStatus.EXPIRED):
            return

        self.full_clean()
        self.updated_at = timezone.now()
        self.status = NotificationStatus.COMPLETE
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
    def is_pending(self):
        return self.status == NotificationStatus.PENDING

    @property
    def is_complete(self):
        return self.status == NotificationStatus.COMPLETE

    @property
    def expired(self):
        return self.expires_at and self.expires_at < timezone.now()
