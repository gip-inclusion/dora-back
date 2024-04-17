import logging
import pprint
import uuid

import django.db.models as models
from django.contrib.postgres.indexes import BrinIndex
from django.core.exceptions import ValidationError


class ActionLog(models.Model):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, verbose_name="identifiant"
    )
    created_at = models.DateTimeField(
        auto_now=True, editable=False, verbose_name="date de création"
    )
    payload = models.JSONField(
        default=dict, null=False, blank=True, verbose_name="contenu brut (JSON)"
    )

    class Meta:
        verbose_name = "historique des actions"
        verbose_name_plural = "historique des actions"
        indexes = (
            BrinIndex(
                fields=("created_at",),
                name="idx_%(app_label)s_%(class)s_created_at",
                autosummarize=True,
            ),
        )

    def __repr__(self):
        return pprint.pformat(
            {"_id": str(self.pk), "_createdAt": str(self.created_at)} | self.payload
        )

    def __str__(self):
        return f"{str(self.pk)} - {self.payload.get('level')}"

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.clean()
        super().save(force_insert, force_update, using, update_fields)

    def clean(self):
        # on s'assure de la présence de certains champs dans le contenu JSON :
        # - un message
        # - le niveau du log
        if not self.payload.get("msg"):
            raise ValidationError("Le contenu du log doit contenir un champ 'msg'")

        if self.payload.get("level") not in logging._levelToName.values():
            raise ValidationError(
                "Le contenu du log doit contenir un champ 'level' conforme"
            )
