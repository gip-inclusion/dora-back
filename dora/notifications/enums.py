from django.db import models


class NotificationStatus(models.TextChoices):
    PENDING = "pending"
    COMPLETE = "complete"
    EXPIRED = "expired"


class TaskType(models.TextChoices):
    ORPHAN_STRUCTURES = "orphan_structures"
    ...

    # catch-all: pour des cas de tests, ou "one-shot"
    GENERIC_TASK = "generic_task"
