import uuid

from django.conf import settings
from django.contrib.gis.db import models
from django.contrib.postgres.fields import ArrayField
from django.db.models.fields import CharField
from django.utils.crypto import get_random_string
from django.utils.text import slugify

from dora.structures.models import Structure, StructureMember


def make_unique_slug(instance, parent_slug, value, length=20):
    model = instance.__class__
    base_slug = parent_slug + "-" + slugify(value)[:length]
    unique_slug = base_slug
    while model.objects.filter(slug=unique_slug).exists():
        unique_slug = (
            base_slug + "-" + get_random_string(4, "abcdefghijklmnopqrstuvwxyz")
        )
    return unique_slug


class ServiceCategories(models.TextChoices):
    MOBILITY = ("MO", "Mobilité")
    HOUSING = ("HO", "Logement")
    CHILD_CARE = ("CC", "Garde d’enfant")


# Subcategories are prefixed by their category
class ServiceSubCategories(models.TextChoices):

    MO_MOBILITY = ("MO-MO", "Quand on veut se déplacer")
    MO_WORK = ("MO-WK", "Quand on reprend un emploi ou une formation")
    MO_LICENSE = ("MO-LI", "Quand on veut passer son permis")
    MO_VEHICLE = ("MO-VE", "Quand on a son permis mais pas de véhicule")
    MO_MAINTENANCE = ("MO-MA", "Quand on doit entretenir son véhicule")

    HO_SHORT = ("HO-SH", "Hebergement de courte durée")
    HO_ACCESS = ("HO-AC", "Accéder au logement")
    HO_KEEP = ("HO-KE", "Conserver son logement")

    CC_INFO = ("CC-IN", "Information et accompagnement des parents")
    CC_TEMP = ("CC-TM", "Garde ponctuelle")
    CC_LONG = ("CC-LG", "Garde pérenne")
    CC_EXTRACURRICULAR = ("CC-EX", "Garde périscolaire")


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
    FORM = ("FO", "Envoyer le formulaire d’adhésion")
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


class CustomizableChoice(models.Model):
    name = models.CharField(max_length=140)
    structure = models.ForeignKey(
        Structure,
        on_delete=models.CASCADE,
        db_index=True,
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=["name", "structure"],
                name="%(app_label)s_unique_%(class)s_by_structure",
            )
        ]

    def __str__(self):
        return self.name


class AccessCondition(CustomizableChoice):
    class Meta(CustomizableChoice.Meta):
        verbose_name = "Critère d’admission"
        verbose_name_plural = "Critères d’admission"


class ConcernedPublic(CustomizableChoice):
    class Meta(CustomizableChoice.Meta):
        verbose_name = "Public concerné"
        verbose_name_plural = "Publics concernés"


class Requirement(CustomizableChoice):
    class Meta(CustomizableChoice.Meta):
        verbose_name = "Pré-requis ou compétence"
        verbose_name_plural = "Pré-requis ou compétences"


class Credential(CustomizableChoice):
    class Meta(CustomizableChoice.Meta):
        verbose_name = "Justificatif à fournir"
        verbose_name_plural = "Justificatifs à fournir"


class Service(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(blank=True, null=True, unique=True)

    ##############
    # Presentation
    name = models.CharField(verbose_name="Nom de l’offre", max_length=140)
    short_desc = models.TextField(verbose_name="Résumé", max_length=280, blank=True)
    full_desc = models.TextField(
        verbose_name="Descriptif complet de l’offre", blank=True
    )

    ##########
    # Typology
    kinds = ArrayField(
        models.CharField(max_length=2, choices=ServiceKind.choices),
        verbose_name="Type de service",
        db_index=True,
        blank=True,
        default=list,
    )
    category = models.CharField(
        max_length=2,
        choices=ServiceCategories.choices,
        verbose_name="Catégorie principale",
        db_index=True,
        blank=True,
    )

    subcategories = ArrayField(
        models.CharField(max_length=6, choices=ServiceSubCategories.choices),
        verbose_name="Sous-catégorie",
        blank=True,
        default=list,
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
    fee_details = models.TextField(verbose_name="Détail des frais", blank=True)

    ############
    # Modalities

    beneficiaries_access_modes = ArrayField(
        models.CharField(max_length=2, choices=BeneficiaryAccessMode.choices),
        verbose_name="Comment mobiliser la solution en tant que bénéficiaire",
        blank=True,
        default=list,
    )
    beneficiaries_access_modes_other = CharField(
        verbose_name="Autre", max_length=280, blank=True
    )
    coach_orientation_modes = ArrayField(
        models.CharField(max_length=2, choices=CoachOrientationMode.choices),
        verbose_name="Comment orienter un bénéficiaire en tant qu’accompagnateur",
        blank=True,
        default=list,
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
    online_form = models.URLField(
        verbose_name="Formulaire en ligne à compléter",
        blank=True,
    )

    ########################
    # Practical informations

    # Contact

    contact_name = models.CharField(
        max_length=140, verbose_name="Nom du contact référent", blank=True
    )
    contact_phone = models.CharField(
        verbose_name="Numéro de téléphone", max_length=10, blank=True
    )
    contact_email = models.EmailField(verbose_name="Courriel", blank=True)
    is_contact_info_public = models.BooleanField(
        verbose_name="Rendre mes informations publiques",
        default=False,
    )

    # Location

    location_kinds = ArrayField(
        models.CharField(max_length=2, choices=LocationKind.choices),
        verbose_name="Lieu de déroulement",
        blank=True,
        default=list,
    )

    remote_url = models.URLField(verbose_name="Lien visioconférence", blank=True)
    address1 = models.CharField(verbose_name="Adresse", max_length=255, blank=True)
    address2 = models.CharField(
        verbose_name="Compléments d’adresse", max_length=255, blank=True
    )
    postal_code = models.CharField(verbose_name="Code postal", max_length=5, blank=True)
    city_code = models.CharField(verbose_name="Code INSEE", max_length=5, blank=True)
    city = models.CharField(verbose_name="Ville", max_length=200, blank=True)
    geom = models.PointField(
        srid=4326, geography=True, spatial_index=True, null=True, blank=True
    )

    # Duration

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

    ##########
    # Metadata

    structure = models.ForeignKey(
        Structure,
        verbose_name="Structure",
        on_delete=models.CASCADE,
        db_index=True,
        related_name="services",
    )
    is_draft = models.BooleanField(default=True)

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

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = make_unique_slug(self, self.structure.slug, self.name)
        return super().save(*args, **kwargs)

    def can_write(self, user):
        return (
            user.is_staff
            or StructureMember.objects.filter(
                structure_id=self.structure_id, user_id=user.id
            ).exists()
        )
