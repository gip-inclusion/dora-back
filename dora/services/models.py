import logging
import uuid

from django.conf import settings
from django.contrib.gis.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.cache import cache
from django.db.models import CharField, Q
from django.utils.crypto import get_random_string
from django.utils.text import slugify

from dora.admin_express.models import AdminDivisionType
from dora.core.models import EnumModel, LogItem, ModerationMixin
from dora.structures.models import Structure, StructureMember

from .enums import ServiceStatus

logger = logging.getLogger(__name__)


def make_unique_slug(instance, parent_slug, value, length=20):
    base_slug = parent_slug + "-" + slugify(value)[:length]
    unique_slug = base_slug
    while Service.objects.filter(
        slug=unique_slug
    ).exists() or ServiceModel.objects.filter(slug=unique_slug):
        unique_slug = (
            base_slug + "-" + get_random_string(4, "abcdefghijklmnopqrstuvwxyz")
        )
    return unique_slug


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

    def _get_cache_key(self, fct_name):
        return f"{self.__class__.__name__}-{fct_name}-{self.pk}"

    def __str__(self):
        cachekey = self._get_cache_key("__str__")
        cached_value = cache.get(cachekey)
        if not cached_value:
            cached_value = f'{self.name} ({"global" if not self.structure else self.structure.name})'
            cache.set(cachekey, cached_value)
        return cached_value

    def save(self, *args, **kwargs):
        cache.delete(self._get_cache_key("__str__"))
        return super().save(*args, **kwargs)


class AccessCondition(CustomizableChoice):
    class Meta(CustomizableChoice.Meta):
        verbose_name = "Critère d’admission"
        verbose_name_plural = "Critères d’admission"


class ConcernedPublic(CustomizableChoice):
    class Meta(CustomizableChoice.Meta):
        verbose_name = "Public concerné"
        verbose_name_plural = "Publics concernés"


class ServiceFee(EnumModel):
    class Meta:
        verbose_name = "Frais à charge"


class Requirement(CustomizableChoice):
    class Meta(CustomizableChoice.Meta):
        verbose_name = "Pré-requis ou compétence"
        verbose_name_plural = "Pré-requis ou compétences"


class Credential(CustomizableChoice):
    class Meta(CustomizableChoice.Meta):
        verbose_name = "Justificatif à fournir"
        verbose_name_plural = "Justificatifs à fournir"


class ServiceCategory(EnumModel):
    class Meta:
        verbose_name = "Catégorie principale"
        verbose_name_plural = "Catégories principales"


class ServiceSubCategory(EnumModel):
    class Meta:
        verbose_name = "Sous-catégorie"


class ServiceKind(EnumModel):
    class Meta:
        verbose_name = "Type de service"
        verbose_name_plural = "Types de service"


class BeneficiaryAccessMode(EnumModel):
    class Meta:
        verbose_name = "Mode d'orientation bénéficiaire"
        verbose_name_plural = "Modes d'orientation bénéficiaire"


class CoachOrientationMode(EnumModel):
    class Meta:
        verbose_name = "Mode d'orientation accompagnateur"
        verbose_name_plural = "Modes d'orientation accompagnateur"


class LocationKind(EnumModel):
    class Meta:
        verbose_name = "Lieu de déroulement"
        verbose_name_plural = "Lieux de déroulement"


class CustomizableChoicesSet(models.Model):
    name = models.CharField(max_length=140)

    creation_date = models.DateTimeField(auto_now_add=True)
    modification_date = models.DateTimeField(auto_now=True)

    access_conditions = models.ManyToManyField(
        AccessCondition, verbose_name="Critères d’admission", blank=True
    )
    concerned_public = models.ManyToManyField(
        ConcernedPublic, verbose_name="Publics concernés", blank=True
    )
    requirements = models.ManyToManyField(
        Requirement,
        verbose_name="Pré-requis ou compétences ?",
        blank=True,
    )
    credentials = models.ManyToManyField(
        Credential, verbose_name="Justificatifs à fournir ?", blank=True
    )

    class Meta:
        verbose_name = "Liste de choix"
        verbose_name_plural = "Listes de choix"

    def __str__(self):
        return f"{self.name} (#{self.pk})"


class ServiceManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_model=False)

    def published(self):
        return self.filter(status=ServiceStatus.PUBLISHED)

    def draft(self):
        return self.filter(status=ServiceStatus.DRAFT)

    def active(self):
        return self.exclude(status=ServiceStatus.ARCHIVED)

    def archived(self):
        return self.filter(status=ServiceStatus.ARCHIVED)


class Service(ModerationMixin, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=100, blank=True, null=True, unique=True)

    ##############
    # Presentation
    name = models.CharField(verbose_name="Nom de l’offre", max_length=140)
    short_desc = models.TextField(verbose_name="Résumé", max_length=280, blank=True)
    full_desc = models.TextField(
        verbose_name="Descriptif complet de l’offre", blank=True
    )

    ##########
    # Typology

    kinds = models.ManyToManyField(
        ServiceKind,
        verbose_name="Type de service",
        blank=True,
    )

    categories = models.ManyToManyField(
        ServiceCategory,
        verbose_name="Catégories principales",
        blank=True,
    )

    subcategories = models.ManyToManyField(
        ServiceSubCategory,
        verbose_name="Sous-catégorie",
        blank=True,
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
    fee_condition = models.ForeignKey(
        ServiceFee,
        verbose_name="Frais à charge",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    fee_details = models.TextField(verbose_name="Détail des frais", blank=True)

    ############
    # Modalities

    beneficiaries_access_modes = models.ManyToManyField(
        BeneficiaryAccessMode,
        verbose_name="Comment mobiliser la solution en tant que bénéficiaire",
        blank=True,
    )

    beneficiaries_access_modes_other = CharField(
        verbose_name="Autre", max_length=280, blank=True
    )

    coach_orientation_modes = models.ManyToManyField(
        CoachOrientationMode,
        verbose_name="Comment orienter un bénéficiaire en tant qu’accompagnateur",
        blank=True,
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

    location_kinds = models.ManyToManyField(
        LocationKind,
        verbose_name="Lieu de déroulement",
        blank=True,
    )

    remote_url = models.URLField(verbose_name="Lien visioconférence", blank=True)
    address1 = models.CharField(verbose_name="Adresse", max_length=255, blank=True)
    address2 = models.CharField(
        verbose_name="Compléments d’adresse", max_length=255, blank=True
    )
    postal_code = models.CharField(verbose_name="Code postal", max_length=5, blank=True)
    city_code = models.CharField(verbose_name="Code INSEE", max_length=5, blank=True)
    city = models.CharField(verbose_name="Ville", max_length=255, blank=True)
    geom = models.PointField(
        srid=4326, geography=True, spatial_index=True, null=True, blank=True
    )

    diffusion_zone_type = models.CharField(
        max_length=10,
        choices=AdminDivisionType.choices,
        verbose_name="Zone de diffusion",
        db_index=True,
        blank=True,
    )
    diffusion_zone_details = models.CharField(max_length=9, db_index=True, blank=True)
    qpv_or_zrr = models.BooleanField(default=False)

    # Duration
    recurrence = models.CharField(verbose_name="Autre", max_length=140, blank=True)

    suspension_date = models.DateField(
        verbose_name="À partir d’une date", null=True, blank=True, db_index=True
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

    status = models.CharField(
        max_length=20,
        choices=ServiceStatus.choices,
        verbose_name="Statut",
        db_index=True,
        null=True,
        blank=True,
    )
    # TODO: to clean
    is_draft = models.BooleanField(default=True)
    # TODO: to clean
    is_suggestion = models.BooleanField(default=False)

    creation_date = models.DateTimeField(auto_now_add=True)
    modification_date = models.DateTimeField(blank=True, null=True)
    publication_date = models.DateTimeField(blank=True, null=True)

    # Temps passé (en seconde) sur le formulaire de création d'un service - avant la *toute* première publication
    # Plus exactement : temps de contribution cumulé en brouillon + temps de contribution final menant au statut "publié"
    filling_duration = models.IntegerField(null=True, blank=True, default=None)

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

    is_model = models.BooleanField(default=False)
    can_update_categories = models.BooleanField(
        default=True,
        verbose_name="En tant que modèle, la mise à jour des thématiques est-elle possible ?",
    )
    model = models.ForeignKey(
        "ServiceModel",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="copies",
    )
    sync_checksum = models.CharField(max_length=32, blank=True)
    last_sync_checksum = models.CharField(max_length=32, blank=True)

    last_draft_notification_date = models.DateTimeField(
        blank=True, null=True, db_index=True
    )

    customizable_choices_set = models.ForeignKey(
        CustomizableChoicesSet,
        verbose_name="Liste de choix",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    objects = ServiceManager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_status_not_empty_except_models",
                check=Q(is_model=False) | Q(status__isnull=True),
            )
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return self.get_frontend_url()

    def get_previous_status(self):
        try:
            item = ServiceStatusHistoryItem.objects.filter(service=self).latest()
            if item.new_status != self.status:
                logging.error(
                    "Inconsistent status history",
                    extra={
                        "service": self.slug,
                        "current_status": self.status,
                        "reported_current_status": item.new_status,
                        "history_item": item.id,
                    },
                )
            return item.previous_status
        except ServiceStatusHistoryItem.DoesNotExist:
            return None

    def save(self, user=None, *args, **kwargs):
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

    def get_frontend_url(self):
        return f"{settings.FRONTEND_URL}/services/{self.slug}"

    def get_admin_url(self):
        return f"https://{settings.ALLOWED_HOSTS[0]}/services/service/{self.id}/change"

    def log_note(self, user, msg):
        LogItem.objects.create(service=self, user=user, message=msg.strip())


class ServiceModelManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_model=True)


class ServiceModel(Service):
    objects = ServiceModelManager()

    class Meta:
        verbose_name = "Modèle"
        proxy = True


class ServiceStatusHistoryItem(models.Model):
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="status_history_item"
    )
    date = models.DateTimeField(auto_now=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    new_status = models.CharField(
        max_length=20,
        choices=ServiceStatus.choices,
        verbose_name="Nouveau statut",
        db_index=True,
    )

    previous_status = models.CharField(
        max_length=20,
        choices=ServiceStatus.choices,
        verbose_name="Statut précédent",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-date"]
        verbose_name = "Historique des statuts de service"
        get_latest_by = "date"

    def __str__(self):
        return f"{self.service_id} {self.previous_status} => {self.new_status}"


class ServiceModificationHistoryItem(models.Model):
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="history_item"
    )
    date = models.DateTimeField(auto_now=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    fields = ArrayField(
        models.CharField(
            max_length=50,
        ),
    )
    status = models.CharField(
        max_length=20,
        choices=ServiceStatus.choices,
        verbose_name="Statut après modification",
        default="",
        blank=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-date"]
        verbose_name = "Historique de modification de service"
