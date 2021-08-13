import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.crypto import get_random_string
from django.utils.text import slugify


# From: https://github.com/betagouv/itou/blob/master/itou/utils/validators.py
def validate_siret(siret):
    if not siret.isdigit() or len(siret) != 14:
        raise ValidationError("Le numéro SIRET doit être composé de 14 chiffres.")


def make_unique_slug(instance, value, length=20):
    model = instance.__class__
    base_slug = slugify(value)[:length]
    unique_slug = base_slug
    while model.objects.filter(slug=unique_slug).exists():
        unique_slug = (
            base_slug + "-" + get_random_string(4, "abcdefghijklmnopqrstuvwxyz")
        )
    return unique_slug


class StructureKinds(models.TextChoices):
    MOBILITY = ("MO", "Mobilité")
    HOUSING = ("HO", "Logement")
    CHILD_CARE = ("CC", "Garde d’enfant")


class StructureTypology(models.TextChoices):
    # Prescripteurs habilités
    # https://github.com/betagouv/itou/blob/master/itou/prescribers/models.py#L91
    PE = "PE", "Pôle emploi"
    CAP_EMPLOI = "CAP_EMPLOI", "CAP emploi"
    ML = "ML", "Mission locale"
    DEPT = "DEPT", "Service social du conseil départemental"
    SPIP = "SPIP", "SPIP — Service pénitentiaire d'insertion et de probation"
    PJJ = "PJJ", "PJJ — Protection judiciaire de la jeunesse"
    CCAS = (
        "CCAS",
        "CCAS — Centre communal d'action sociale ou centre intercommunal d'action sociale",
    )
    PLIE = "PLIE", "PLIE — Plan local pour l'insertion et l'emploi"
    CHRS = "CHRS", "CHRS — Centre d'hébergement et de réinsertion sociale"
    CIDFF = (
        "CIDFF",
        "CIDFF — Centre d'information sur les droits des femmes et des familles",
    )
    PREVENTION = "PREVENTION", "Service ou club de prévention"
    AFPA = (
        "AFPA",
        "AFPA — Agence nationale pour la formation professionnelle des adultes",
    )
    PIJ_BIJ = "PIJ_BIJ", "PIJ-BIJ — Point/Bureau information jeunesse"
    CAF = "CAF", "CAF — Caisse d'allocation familiale"
    CADA = "CADA", "CADA — Centre d'accueil de demandeurs d'asile"
    ASE = "ASE", "ASE — Aide sociale à l'enfance"
    CAVA = "CAVA", "CAVA — Centre d'adaptation à la vie active"
    CPH = "CPH", "CPH — Centre provisoire d'hébergement"
    CHU = "CHU", "CHU — Centre d'hébergement d'urgence"
    OACAS = (
        "OACAS",
        (
            "OACAS — Structure porteuse d'un agrément national organisme "
            "d'accueil communautaire et d'activité solidaire"
        ),
    )
    # SIAE
    # https://github.com/betagouv/itou/blob/master/itou/siaes/models.py#L169
    EI = "EI", "SIAE — Entreprise d'insertion"
    AI = ("AI", "SIAE — Association intermédiaire")
    ACI = ("ACI", "SIAE — Atelier chantier d'insertion")
    ACIPHC = (
        "ACIPHC",
        "SIAE — Atelier chantier d'insertion premières heures en chantier",
    )
    ETTI = ("ETTI", "SIAE — Entreprise de travail temporaire d'insertion")
    EITI = ("EITI", "SIAE — Entreprise d'insertion par le travail indépendant")
    GEIQ = (
        "GEIQ",
        "SIAE — Groupement d'employeurs pour l'insertion et la qualification",
    )
    EA = ("EA", "SIAE — Entreprise adaptée")
    EATT = ("EATT", "SIAE — Entreprise adaptée de travail temporaire")

    OTHER = "OTHER", "Autre"


class Structure(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    siret = models.CharField(
        verbose_name="Siret", max_length=14, validators=[validate_siret], unique=True
    )
    typology = models.CharField(
        max_length=10,
        choices=StructureTypology.choices,
    )
    slug = models.SlugField(blank=True, null=True, unique=True)
    name = models.CharField(verbose_name="Nom", max_length=255)
    short_desc = models.CharField(max_length=280)
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
    email = models.EmailField()
    postal_code = models.CharField(max_length=5)
    city_code = models.CharField(max_length=5, blank=True)
    city = models.CharField(max_length=255)
    address1 = models.CharField(max_length=255)
    address2 = models.CharField(max_length=255, blank=True)
    has_services = models.BooleanField(default=False, blank=True)
    ape = models.CharField(max_length=6, blank=True)
    longitude = models.FloatField(blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)

    creation_date = models.DateTimeField(auto_now_add=True)
    modification_date = models.DateTimeField(auto_now=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True
    )
    last_editor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
    )

    # TODO: opening_hours, edit history, moderation

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = make_unique_slug(self, self.name)
        return super().save(*args, **kwargs)
