from django.db import models


class NotificationStatus(models.TextChoices):
    PENDING = "pending"
    COMPLETE = "complete"
    EXPIRED = "expired"


class TaskType(models.TextChoices):
    ORPHAN_STRUCTURES = "orphan_structures"
    INVITED_USERS = "invited_users"
    SELF_INVITED_USERS = "self_invited_users"
    ...

    # catch-all: pour des cas de tests, ou "one-shot"
    GENERIC_TASK = "generic_task"
