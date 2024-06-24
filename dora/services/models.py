import logging
import uuid
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.gis.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.cache import cache
from django.db.models import CharField, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.text import slugify

from dora.admin_express.models import EPCI, AdminDivisionType, City, Department, Region
from dora.admin_express.utils import arrdt_to_main_insee_code, get_clean_city_name
from dora.core.constants import WGS84
from dora.core.models import EnumModel, LogItem, ModerationMixin
from dora.structures.models import Structure

from .enums import ServiceStatus, ServiceUpdateStatus

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


class SavedSearchFrequency(models.TextChoices):
    NEVER = "NEVER", "Jamais"
    TWO_WEEKS = "TWO_WEEKS", "Tous les 15 jours"
    MONTHLY = "MONTHLY", "Mensuel"


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


class ServiceSource(EnumModel):
    class Meta:
        verbose_name = "Source"


class ServiceManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_model=False)

    def published(self):
        return self.filter(status=ServiceStatus.PUBLISHED)

    def update_advised(self):
        return self.filter(
            status=ServiceStatus.PUBLISHED,
            modification_date__lte=timezone.now()
            - timedelta(days=settings.NUM_DAYS_BEFORE_ADVISED_SERVICE_UPDATE),
        )

    def update_mandatory(self):
        return self.filter(
            status=ServiceStatus.PUBLISHED,
            modification_date__lte=timezone.now()
            - timedelta(days=settings.NUM_DAYS_BEFORE_MANDATORY_SERVICE_UPDATE),
        )

    def draft(self):
        return self.filter(status=ServiceStatus.DRAFT)

    def active(self):
        return self.exclude(status=ServiceStatus.ARCHIVED)

    def archived(self):
        return self.filter(status=ServiceStatus.ARCHIVED)


def get_diffusion_zone_details_display(
    diffusion_zone_type: AdminDivisionType,
    diffusion_zone_details: str,
) -> str:
    if diffusion_zone_type == AdminDivisionType.COUNTRY:
        return "France entière"

    if diffusion_zone_type == AdminDivisionType.CITY:
        city = City.objects.get_from_code(diffusion_zone_details)
        # TODO: we'll probably want to log and correct a missing code
        return f"{city.name} ({city.department})" if city else ""

    item = None

    if diffusion_zone_type == AdminDivisionType.EPCI:
        item = EPCI.objects.get_from_code(diffusion_zone_details)
    elif diffusion_zone_type == AdminDivisionType.DEPARTMENT:
        item = Department.objects.get_from_code(diffusion_zone_details)
    elif diffusion_zone_type == AdminDivisionType.REGION:
        item = Region.objects.get_from_code(diffusion_zone_details)
    # TODO: we'll probably want to log and correct a missing code
    return item.name if item else ""


def get_update_status(status: ServiceStatus, modification_date: datetime):
    if status != ServiceStatus.PUBLISHED:
        return ServiceUpdateStatus.NOT_NEEDED

    diff = timezone.now() - modification_date
    if diff >= timedelta(days=240):
        return ServiceUpdateStatus.REQUIRED
    elif diff >= timedelta(days=180):
        return ServiceUpdateStatus.NEEDED

    return ServiceUpdateStatus.NOT_NEEDED


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
    # lecture seule
    city = models.CharField(verbose_name="Ville", max_length=255, blank=True)
    #
    geom = models.PointField(
        srid=WGS84, geography=True, spatial_index=True, null=True, blank=True
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

    recurrence = models.CharField(verbose_name="Récurrence", max_length=140, blank=True)

    suspension_date = models.DateField(
        verbose_name="Jusqu’au", null=True, blank=True, db_index=True
    )

    appointment_link = models.URLField(
        verbose_name="Lien de prise de rendez-vous", blank=True
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

    creation_date = models.DateTimeField(auto_now_add=True)
    modification_date = models.DateTimeField(blank=True, null=True)
    publication_date = models.DateTimeField(blank=True, null=True)

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

    model = models.ForeignKey(
        "ServiceModel",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="copies",
    )
    sync_checksum = models.CharField(max_length=32, blank=True)
    last_sync_checksum = models.CharField(max_length=32, blank=True)

    use_inclusion_numerique_scheme = models.BooleanField(default=False)

    source = models.ForeignKey(
        ServiceSource, null=True, blank=True, on_delete=models.PROTECT
    )
    data_inclusion_id = models.TextField(blank=True, db_index=True)
    data_inclusion_source = models.TextField(blank=True, db_index=True)

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
        self.city = get_clean_city_name(self.city_code)
        return super().save(*args, **kwargs)

    def can_read(self, user):
        return self.status == ServiceStatus.PUBLISHED or (
            user.is_authenticated
            and (
                user.is_staff
                or self.structure.is_manager(user)
                or self.structure.is_member(user)
            )
        )

    def can_write(self, user):
        return user.is_authenticated and (
            user.is_staff
            or self.structure.is_manager(user)
            or self.structure.is_member(user)
        )

    def get_frontend_url(self):
        return f"{settings.FRONTEND_URL}/services/{self.slug}"

    def get_admin_url(self):
        return f"https://{settings.ALLOWED_HOSTS[0]}/services/service/{self.id}/change"

    def log_note(self, user, msg):
        LogItem.objects.create(service=self, user=user, message=msg.strip())

    def get_diffusion_zone_details_display(self):
        return get_diffusion_zone_details_display(
            self.diffusion_zone_type,
            self.diffusion_zone_details,
        )

    def get_update_status(self):
        return get_update_status(
            status=self.status, modification_date=self.modification_date
        )

    def is_orientable_partial_compute(self):
        structure_blacklisted = False
        for siren in settings.ORIENTATION_SIRENE_BLACKLIST:
            if self.structure.siret and self.structure.siret.startswith(siren):
                structure_blacklisted = True
                break
        return bool(
            self.status == ServiceStatus.PUBLISHED
            and not self.structure.disable_orientation_form
            and not structure_blacklisted
            and self.contact_email
        )

    def is_orientable(self):
        return self.is_orientable_partial_compute and (
            self.coach_orientation_modes.filter(
                Q(value="envoyer-courriel") | Q(value="envoyer-fiche-prescription")
            ).exists()
            or self.beneficiaries_access_modes.filter(value="envoyer-courriel").exists()
        )


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


class Bookmark(models.Model):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)
    service = models.ForeignKey("Service", on_delete=models.CASCADE, null=True)
    di_id = models.TextField(blank=True)
    creation_date = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "service"],
                condition=Q(service__isnull=False),
                name="%(app_label)s_unique_service_bookmark",
            ),
            models.UniqueConstraint(
                fields=["user", "di_id"],
                condition=~Q(di_id=""),
                name="%(app_label)s_unique_di_bookmark",
            ),
        ]


class SavedSearch(models.Model):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)
    creation_date = models.DateTimeField(auto_now_add=True, db_index=True)
    city_code = models.CharField(verbose_name="Code INSEE de la recherche")
    city_label = models.CharField(verbose_name="Label de la ville")
    category = models.ForeignKey(
        ServiceCategory,
        verbose_name="Thématique",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    subcategories = models.ManyToManyField(
        ServiceSubCategory,
        verbose_name="Besoins",
        blank=True,
    )
    kinds = models.ManyToManyField(
        ServiceKind, verbose_name="Type de service", blank=True
    )
    fees = models.ManyToManyField(ServiceFee, verbose_name="Frais à charge", blank=True)
    location_kinds = models.ManyToManyField(
        LocationKind,
        verbose_name="Lieu de déroulement",
        blank=True,
    )
    frequency = models.CharField(
        max_length=10,
        choices=SavedSearchFrequency.choices,
        default=SavedSearchFrequency.TWO_WEEKS,
        verbose_name="Fréquence",
    )
    last_notification_date = models.DateField(default=datetime.now)

    class Meta:
        verbose_name = "Recherche sauvegardé"
        verbose_name_plural = "Recherches sauvegardées"

    def get_recent_services(self, cutoff_date):
        from dora import data_inclusion

        di_client = (
            data_inclusion.di_client_factory()
            if settings.INCLUDES_DI_SERVICES_IN_SAVED_SEARCH_NOTIFICATIONS
            else None
        )

        category = None
        if self.category:
            category = self.category

        subcategories = None
        if self.subcategories.exists():
            subcategories = self.subcategories.values_list("value", flat=True)

        kinds = None
        if self.kinds.exists():
            kinds = self.kinds.values_list("value", flat=True)

        fees = None
        if self.fees.exists():
            fees = self.fees.values_list("value", flat=True)

        location_kinds = None
        if self.location_kinds.exists():
            location_kinds = self.location_kinds.values_list("value", flat=True)

        # Récupération des résultats de la recherche
        from .search import search_services

        city_code = arrdt_to_main_insee_code(self.city_code)
        city = get_object_or_404(City, pk=city_code)

        results = search_services(
            None,
            self.city_code,
            city,
            [category.value] if category and not subcategories else None,
            subcategories,
            kinds,
            fees,
            location_kinds,
            di_client,
        )

        # On garde les contenus qui ont été publiés depuis la dernière notification
        return [
            r
            for r in results
            if datetime.fromisoformat(r["publication_date"]).date() > cutoff_date
        ]
