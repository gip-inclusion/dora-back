import uuid

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models


# From: https://github.com/betagouv/itou/blob/master/itou/utils/validators.py
def validate_siret(siret):
    if not siret.isdigit() or len(siret) != 14:
        raise ValidationError("Le numéro SIRET doit être composé de 14 chiffres.")


class SolutionThemes(models.TextChoices):
    MOBILITY_THEME = "MO", "Mobilité"
    HOUSING_THEME = "HO", "Logement – Hébergement"
    CHILD_CARE_THEME = "CC", "Garde d'enfant"
    OTHER_THEME = "OT", "Autre"


class SolutionKind(models.TextChoices):
    MATERIAL_KIND = (
        "MK",
        "Solutions matérielle (ex : mise à disposition local, garde d’enfant ponctuelle, …)",
    )
    FINANCIAL_KIND = "FK", "Solution financière"
    SUPPORT_KIND = "SK", "Solution d’accompagnement"


class Structure(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    siret = models.CharField(
        verbose_name="Siret",
        max_length=14,
        validators=[validate_siret],
    )
    name = models.CharField(verbose_name="Nom", max_length=255)
    short_desc = models.TextField(blank=True)
    url = models.URLField(blank=True)
    full_desc = models.TextField(blank=True)
    facebook_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    ressources_url = models.URLField(blank=True)
    phone = models.CharField(max_length=10, blank=True)
    faq_url = models.URLField(blank=True)
    contact_form_url = models.URLField(blank=True)
    email = models.EmailField(blank=True)
    postal_code = models.CharField(max_length=5)
    city_code = models.CharField(max_length=5)
    city = models.CharField(max_length=200)
    address = models.TextField()
    has_solutions = models.BooleanField()
    solutions_themes = ArrayField(
        models.CharField(max_length=2, choices=SolutionThemes.choices),
        blank=True,
        default=list,
    )
    solutions_kinds = ArrayField(
        models.CharField(max_length=2, choices=SolutionKind.choices),
        blank=True,
        default=list,
    )
    other_themes = ArrayField(
        models.CharField(max_length=200),
        blank=True,
        default=list,
    )
    creation_date = models.DateTimeField(auto_now_add=True)
    modification_date = models.DateTimeField(auto_now=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True
    )

    # TODO: opening_hours, edit history, moderation
