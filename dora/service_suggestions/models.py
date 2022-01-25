import uuid

from django.conf import settings
from django.db import models

from dora.core.validators import validate_siret


class ServiceSuggestion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    siret = models.CharField(
        verbose_name="Siret", max_length=14, validators=[validate_siret], db_index=True
    )
    name = models.CharField(verbose_name="Nom de l’offre", max_length=140)
    creation_date = models.DateTimeField(auto_now_add=True)
    contents = models.JSONField(default=dict)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="+",
    )
