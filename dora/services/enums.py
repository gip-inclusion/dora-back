from django.db import models


class ServiceStatus(models.TextChoices):
    SUGGESTION = "SUGGESTION", "Suggestion"
    DRAFT = "DRAFT", "Draft"
    PUBLISHED = "PUBLISHED", "Published"
    ARCHIVED = "ARCHIVED", "Archived"


class ServiceUpdateStatus:
    NEEDED = "NEEDED"
    NOT_NEEDED = "NOT_NEEDED"
    REQUIRED = "REQUIRED"
