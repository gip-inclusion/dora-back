import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from dora.structures.models import Structure, StructurePutativeMember
from dora.users.models import User

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
        related_name="notifications",
    )
    owner_user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name="Utilisateur propriétaire",
        related_name="notifications",
    )
    owner_structureputativemember = models.ForeignKey(
        StructurePutativeMember,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name="Invitation propriétaire",
        related_name="notifications",
    )
    ...

    objects = NotificationQueryset.as_manager()

    def __str__(self):
        return f"ID:{self.pk}, TASK_TYPE:{self.task_type}, STATUS:{self.status}"

    class Meta:
        # ajouter des contraintes pour chaque type de propriètaire possible
        constraints = [
            models.CheckConstraint(
                name="check_owner",
                check=~models.Q(owner_structure=None)
                | ~models.Q(owner_user=None)
                | ~models.Q(owner_structureputativemember=None),
                # | ~models.Q(owner_other_model=None) ...
                # ajouter une contrainte pour chaque type de propriétaire
            ),
            # par définition, une seule définition par propriétaire pour un type de táche donné
            # préferable à `unique_together` si plusieurs contraintes du type
            models.UniqueConstraint(
                name="unique_task_for_structure",
                fields=["task_type", "owner_structure"],
            ),
            models.UniqueConstraint(
                name="unique_task_for_user", fields=["task_type", "owner_user"]
            ),
            models.UniqueConstraint(
                name="unique_task_for_invitation",
                fields=["task_type", "owner_structureputativemember"],
            ),
        ]
        indexes = [
            models.Index(fields=("task_type",)),
            models.Index(fields=("status",)),
            models.Index(fields=("updated_at",)),
        ]

    def _owners(self):
        # liste des propriétaires définis pour la notification
        # incohérent si plus de 1 élément dans la liste
        return [
            getattr(self, f.name)
            for f in self._meta.fields
            if f.name.startswith("owner_") and getattr(self, f.name)
        ]

    def clean(self):
        # quelques vérifications de base pour la présence des FKs
        if len(self._owners()) != 1:
            raise ValidationError("Aucun objet propriétaire attaché")

        if self.task_type not in TaskType.values:
            raise ValidationError("Type de notification inconnu")

        match self.task_type:
            case TaskType.ORPHAN_STRUCTURES:
                if not self.owner_structure_id:
                    raise ValidationError("Aucune structure attachée")
                ...

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
        owners = self._owners()
        match len(owners):
            case 0:
                # ne devrait pas être possible avec la contrainte,
                # sauf si la notification n'est pas sauvegardée
                raise NotificationError(
                    "Aucun propriétaire défini pour la notification"
                )
            case 1:
                [owner] = owners
                return owner
            case _:
                # ne devrait pas être possible avec la contrainte
                raise NotificationError(
                    f"Plusieurs propriétaires définis pour la notification : {owners}"
                )

    @property
    def is_pending(self):
        return self.status == NotificationStatus.PENDING

    @property
    def is_complete(self):
        return self.status == NotificationStatus.COMPLETE

    @property
    def expired(self):
        return self.expires_at and self.expires_at < timezone.now()
