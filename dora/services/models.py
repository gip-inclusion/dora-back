import uuid

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models.fields import CharField

from dora.structures.models import Structure


class ServiceCategories(models.TextChoices):
    MOBILITY = ("MO", "Mobilité")
    HOUSING = ("HO", "Logement")
    CHILD_CARE = ("CC", "Garde d’enfant")


class ServiceSubCategories(models.TextChoices):
    MO_FEES_HELP = ("MFH", "Aide aux frais de déplacements")
    MO_CAR_REPAIR = ("MCR", "Réparation de voitures à prix réduit")


class ServiceKind(models.TextChoices):
    MATERIAL = ("MA", "Aide materielle")
    FINANCIAL = ("FI", "Aide financière")
    SUPPORT = ("SU", "Accompagnement")


class BeneficiaryAccessMode(models.TextChoices):
    ONSITE = ("OS", "Se présenter")
    PHONE = ("PH", "Téléphoner")
    EMAIL = ("EM", "Envoyer un mail")
    OTHER = ("OT", "Autre (préciser)")


class CoachOrientationMode(models.TextChoices):
    PHONE = ("PH", "Téléphoner")
    EMAIL = ("EM", "Envoyer un mail")
    EMAIL_PRESCRIPTION = ("EP", "Envoyer un mail avec une fiche de prescription")
    OTHER = ("OT", "Autre (préciser)")


class LocationKind(models.TextChoices):
    ONSITE = ("OS", "En présentiel")
    REMOTE = ("RE", "À distance")


class RecurrenceKind(models.TextChoices):
    EVERY_DAY = ("DD", "Tous les jours")
    EVERY_WEEK = ("WW", "Toutes les semaines")
    EVERY_MONTH = ("MM", "Tous les mois")
    OTHER = ("OT", "Autre")


class AccessCondition(models.Model):
    name = models.CharField(max_length=140)

    def __str__(self):
        return self.name


class ConcernedPublic(models.Model):
    name = models.CharField(max_length=140)

    def __str__(self):
        return self.name


class Requirement(models.Model):
    name = models.CharField(max_length=140)

    def __str__(self):
        return self.name


class Credential(models.Model):
    name = models.CharField(max_length=140)

    def __str__(self):
        return self.name


class Service(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    ##############
    # Presentation
    name = models.CharField(verbose_name="Nom de l’offre", max_length=140)
    short_desc = models.TextField(
        verbose_name="Résumé",
        max_length=280,
    )
    full_desc = models.TextField(
        verbose_name="Descriptif complet de l’offre", blank=True
    )

    ##########
    # Typology
    kinds = ArrayField(
        models.CharField(max_length=2, choices=ServiceKind.choices),
        verbose_name="Type de service",
        db_index=True,
    )
    categories = ArrayField(
        models.CharField(max_length=2, choices=ServiceCategories.choices),
        verbose_name="Catégorie principale",
        db_index=True,
    )
    subcategories = ArrayField(
        models.CharField(max_length=3, choices=ServiceSubCategories.choices),
        verbose_name="Sous-catégorie",
    )
    is_common_law = models.BooleanField(
        verbose_name="Il s’agit d'un service de Droit commun ?", default=False
    )

    ############
    # Conditions

    access_conditions = models.ManyToManyField(
        AccessCondition, verbose_name="Critères d’admission", blank=True
    )
    concerned_public = models.ManyToManyField(
        ConcernedPublic, verbose_name="Publics concernés", blank=True
    )
    is_cumulative = models.BooleanField(verbose_name="Solution cumulable", default=True)
    has_fee = models.BooleanField(
        verbose_name="Frais à charge pour le bénéficiaire", default=False
    )
    fee_details = models.CharField(
        verbose_name="Détail des frais", max_length=140, blank=True
    )

    ############
    # Modalities

    beneficiaries_access_modes = ArrayField(
        models.CharField(max_length=2, choices=BeneficiaryAccessMode.choices),
        verbose_name="Comment mobiliser la solution en tant que bénéficiaire",
    )
    beneficiaries_access_modes_other = CharField(
        verbose_name="Autre", max_length=280, blank=True
    )
    coach_orientation_modes = ArrayField(
        models.CharField(max_length=2, choices=CoachOrientationMode.choices),
        verbose_name="Comment orienter un bénéficiaire en tant qu’accompagnateur",
    )
    coach_orientation_modes_other = CharField(
        verbose_name="Autre", max_length=280, blank=True
    )
    requirements = models.ManyToManyField(
        Requirement,
        verbose_name="Quels sont les pré-requis ou compétences ?",
        blank=True,
    )
    credentials = models.ManyToManyField(
        Credential, verbose_name="Quels sont les justificatifs à fournir ?", blank=True
    )

    forms = ArrayField(
        models.CharField(max_length=1024),
        verbose_name="Partagez les documents à compléter",
        blank=True,
        default=list,
    )
    online_forms = ArrayField(
        models.CharField(max_length=280),
        verbose_name="Formulaires en ligne à compléter",
        blank=True,
        default=list,
    )

    ########################
    # Practical informations

    # Contact

    contact_name = models.CharField(
        max_length=140,
        verbose_name="Nom du contact référent",
    )
    contact_phone = models.CharField(
        verbose_name="Numéro de téléphone",
        max_length=10,
    )
    contact_email = models.EmailField(
        verbose_name="Courriel",
    )
    is_contact_info_public = models.BooleanField(
        verbose_name="Rendre mes informations publiques",
        default=False,
    )

    # Location

    location_kind = ArrayField(
        models.CharField(max_length=2, choices=LocationKind.choices),
        verbose_name="Lieu de déroulement",
    )

    remote_url = models.URLField(verbose_name="Lien visioconférence", blank=True)
    address1 = models.CharField(
        verbose_name="Adresse",
        max_length=255,
    )
    address2 = models.CharField(
        verbose_name="Compléments d’adresse", max_length=255, blank=True
    )
    postal_code = models.CharField(
        verbose_name="Code postal",
        max_length=5,
    )
    city_code = models.CharField(verbose_name="Code INSEE", max_length=5, blank=True)
    city = models.CharField(
        verbose_name="Ville",
        max_length=200,
    )
    longitude = models.FloatField(blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)

    # Duration

    is_time_limited = models.BooleanField(
        verbose_name="Votre offre est limitée dans le temps ?", default=False
    )
    start_date = models.DateField(verbose_name="Date de début", null=True, blank=True)
    end_date = models.DateField(verbose_name="Date de fin", null=True, blank=True)

    recurrence = models.CharField(
        verbose_name="Récurrences",
        max_length=2,
        choices=RecurrenceKind.choices,
        blank=True,
    )
    recurrence_other = models.CharField(
        verbose_name="Autre", max_length=140, blank=True
    )

    suspension_count = models.IntegerField(
        verbose_name="À partir d’un nombre d’inscriptions", null=True, blank=True
    )
    suspension_date = models.DateField(
        verbose_name="À partir d’une date", null=True, blank=True
    )

    structure = models.ForeignKey(
        Structure,
        verbose_name="",
        on_delete=models.CASCADE,
        db_index=True,
    )

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

    def __str__(self):
        return self.name
