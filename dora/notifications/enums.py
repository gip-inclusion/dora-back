from django.db import models


class NotificationStatus(models.IntegerChoices):
    PENDING = 1
    PROCESSED = 2
    EXPIRED = 3


class TaskType(models.TextChoices):
    ORPHAN_STRUCTURES = "orphan_structures"
