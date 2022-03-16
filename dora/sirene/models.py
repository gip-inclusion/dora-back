from django.contrib.postgres.indexes import GinIndex
from django.db import models

from dora.core.utils import code_insee_to_code_dept


class Establishment(models.Model):
    siret = models.CharField(verbose_name="Siret", max_length=14, primary_key=True)
    siren = models.CharField(verbose_name="Siren", max_length=9)
    name = models.CharField(verbose_name="Nom", max_length=255)

    ape = models.CharField(
        max_length=6,
    )
    address1 = models.CharField(max_length=255, blank=True)
    address2 = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    city_code = models.CharField(max_length=5, db_index=True)
    postal_code = models.CharField(max_length=5)
    is_siege = models.BooleanField()
    longitude = models.FloatField(blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)

    full_search_text = models.TextField()

    class Meta:
        indexes = [
            # https://www.postgresql.org/docs/current/pgtrgm.html#id-1.11.7.40.8
            GinIndex(
                name="full_text_trgm_idx",
                fields=("full_search_text",),
                opclasses=("gin_trgm_ops",),
            )
        ]

    @property
    def department(self) -> str:
        return code_insee_to_code_dept(self.city_code)
