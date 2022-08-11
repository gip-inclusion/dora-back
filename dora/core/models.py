from django.db import models
from django.utils import timezone


class EnumModel(models.Model):
    value = models.CharField(max_length=255, unique=True, db_index=True)
    label = models.CharField(max_length=255)

    class Meta:
        abstract = True

    def __str__(self):
        return self.label


class ModerationStatus(models.TextChoices):
    NEED_INITIAL_MODERATION = (
        "NEED_INITIAL_MODERATION",
        "Première modération nécessaire",
    )
    NEED_NEW_MODERATION = "NEED_NEW_MODERATION", "Nouvelle modération nécessaire"
    IN_PROGRESS = "IN_PROGRESS", "En cours"
    VALIDATED = "VALIDATED", "Validé"


class ModerationMixin(models.Model):

    moderation_status = models.CharField(
        max_length=30,
        choices=ModerationStatus.choices,
        verbose_name="Modération",
        db_index=True,
        null=True,
        blank=True,
    )

    notes = models.TextField(blank=True)

    class Meta:
        abstract = True

    def log_note(self, msg):
        timestamp = timezone.now().strftime("%d/%m/%Y a %Hh%M")
        self.notes = f"{self.notes.strip()}\n{timestamp} | {msg}\n---"
