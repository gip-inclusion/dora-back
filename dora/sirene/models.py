from django.contrib.postgres.indexes import GinIndex
from django.db import models


class Establishment(models.Model):
    siret = models.CharField(verbose_name="Siret", max_length=14, primary_key=True)
    siren = models.CharField(verbose_name="Siren", max_length=9)
    denomination = models.CharField(verbose_name="Nom", max_length=100)
    # https://insee.fr/fr/information/2406147
    ape = models.CharField(max_length=6)
    code_cedex = models.CharField(max_length=9)
    code_commune = models.CharField(max_length=5, db_index=True)
    code_postal = models.CharField(max_length=5)
    complement_adresse = models.CharField(max_length=38)
    distribution_speciale = models.CharField(max_length=26)
    enseigne1 = models.CharField(max_length=50)
    enseigne2 = models.CharField(max_length=50)
    enseigne3 = models.CharField(max_length=50)
    is_siege = models.BooleanField()
    # appartient au champ de l’économie sociale et solidaire
    is_social = models.BooleanField()
    repetition_index = models.CharField(max_length=1)
    libelle_cedex = models.CharField(max_length=100)
    libelle_commune = models.CharField(max_length=100)
    libelle_voie = models.CharField(max_length=100)
    nic = models.CharField(max_length=5)
    numero_voie = models.CharField(max_length=4)
    diffusable = models.BooleanField()
    type_voie = models.CharField(max_length=4)
    denomination_parent = models.TextField(blank=True, default="")
    sigle_parent = models.CharField(max_length=20, blank=True, default="")
    longitude = models.FloatField(blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)

    # TODO: document
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
