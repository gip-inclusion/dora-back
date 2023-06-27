from django.conf import settings
from django.db import models

from dora.services.enums import ServiceStatus, ServiceUpdateStatus
from dora.services.models import Service, ServiceCategory, ServiceSubCategory
from dora.structures.models import Structure
from dora.users.models import MAIN_ACTIVITY_CHOICES


class DeploymentLevel(models.IntegerChoices):
    NONE = 0, "Aucun contact"
    PENDING = 1, "En cours d'échanges"
    STARTED = 2, "Premières saisies de services"
    IN_PROGRESS = 3, "Déploiement en cours"
    FINALIZING = 4, "Finalisation du déploiement"


class DeploymentState(models.Model):
    department_code = models.CharField(max_length=3, blank=True)
    department_name = models.CharField(max_length=230)
    state = models.IntegerField(
        choices=DeploymentLevel.choices,
        verbose_name="État de déploiement",
        default=DeploymentLevel.NONE,
    )

    class Meta:
        verbose_name = "État de déploiement"
        verbose_name_plural = "État de déploiement"

    def __str__(self):
        return f"{self.department_name} ({self.department_code})"


#####################################################################################################
# Analytics
#


class ABTestGroup(models.Model):
    value = models.CharField(max_length=255, primary_key=True)

    def __str__(self):
        return self.value


#############################################################################################
# Modèles abstraits
#


class AbstractAnalyticsEvent(models.Model):
    path = models.CharField(max_length=255)
    date = models.DateTimeField(auto_now_add=True, db_index=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    anonymous_user_hash = models.CharField(max_length=32, blank=True)
    is_logged = models.BooleanField()
    is_staff = models.BooleanField()
    is_manager = models.BooleanField()
    is_an_admin = models.BooleanField()
    user_kind = models.CharField(
        max_length=25,
        choices=MAIN_ACTIVITY_CHOICES,
        verbose_name="Activité principale de l'utilisateur",
        db_index=True,
        blank=True,
    )

    class Meta:
        abstract = True

    def __str__(self):
        return f"`{self.path}` {self.date.isoformat(' ', 'seconds')}"


class AbstractStructureEvent(AbstractAnalyticsEvent):
    structure = models.ForeignKey(
        Structure,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    structure_slug = models.SlugField(blank=True)
    is_structure_member = models.BooleanField()
    is_structure_admin = models.BooleanField()
    structure_department = models.CharField(max_length=3, blank=True, db_index=True)
    structure_city_code = models.CharField(
        verbose_name="Code INSEE de la structure", max_length=5, blank=True
    )

    class Meta:
        abstract = True


class AbstractServiceEvent(AbstractAnalyticsEvent):
    structure = models.ForeignKey(
        Structure,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    structure_slug = models.SlugField(blank=True)
    is_structure_member = models.BooleanField()
    is_structure_admin = models.BooleanField()
    structure_department = models.CharField(max_length=3, blank=True, db_index=True)
    structure_city_code = models.CharField(
        verbose_name="Code INSEE de la structure", max_length=5, blank=True
    )

    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    service_slug = models.SlugField(blank=True)
    update_status = models.CharField(
        max_length=10,
        choices=ServiceUpdateStatus.choices,
        verbose_name="Statut d'actualisation",
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=ServiceStatus.choices,
        verbose_name="Statut",
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True


class AbstractSearchEvent(AbstractAnalyticsEvent):
    categories = models.ManyToManyField(ServiceCategory, blank=True, related_name="+")
    subcategories = models.ManyToManyField(
        ServiceSubCategory, blank=True, related_name="+"
    )
    department = models.CharField(max_length=3, blank=True, db_index=True)
    city_code = models.CharField(
        verbose_name="Code INSEE de la recherche", max_length=5, blank=True
    )
    num_results = models.IntegerField()

    class Meta:
        abstract = True


#############################################################################################
# Vues
#


class PageView(AbstractAnalyticsEvent):
    title = models.CharField(max_length=255, blank=True)


class StructureView(AbstractStructureEvent):
    pass


class ServiceView(AbstractServiceEvent):
    pass


class SearchView(AbstractSearchEvent):
    pass


#############################################################################################
# Événements
#


class MobilisationEvent(AbstractServiceEvent):
    ab_test_groups = models.ManyToManyField(ABTestGroup, blank=True)
