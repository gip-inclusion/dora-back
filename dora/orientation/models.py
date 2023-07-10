import uuid

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models

from dora.services.models import Service
from dora.structures.models import Structure


class ContactPreference(models.TextChoices):
    PHONE = "telephone", "Téléphone"
    EMAIL = "email", "E-mail"
    OTHER = "autre", "Autre"


class OrientationStatus(models.TextChoices):
    PENDING = "ouverte", "Ouverte / En cours de traitement"
    ACCEPTED = "validée", "Validée"
    REJECTED = "refusée", "Refusée"


class Orientation(models.Model):
    query_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)

    # Infos bénéficiaires
    requirements = ArrayField(
        models.CharField(max_length=480),
        verbose_name="Critères",
        blank=True,
        default=list,
    )
    situation = ArrayField(
        models.CharField(max_length=480),
        verbose_name="Situation",
        blank=True,
        default=list,
    )
    situation_other = models.CharField(
        max_length=480, verbose_name="Situation - autre", blank=True
    )

    beneficiary_last_name = models.CharField(
        max_length=140, verbose_name="Nom bénéficiaire", blank=True
    )
    beneficiary_first_name = models.CharField(
        max_length=140, verbose_name="Prénom bénéficiaire", blank=True
    )

    beneficiary_contact_preferences = ArrayField(
        models.CharField(
            choices=ContactPreference.choices,
            max_length=10,
            blank=True,
        ),
        verbose_name="Préférences de contact",
        blank=True,
        default=list,
    )

    beneficiary_phone = models.CharField(
        verbose_name="Tel bénéficiaire", max_length=10, blank=True
    )
    beneficiary_email = models.EmailField(
        verbose_name="Courriel bénéficiaire", blank=True
    )
    beneficiary_other_contact_method = models.CharField(
        verbose_name="Autre méthode de contact bénéficiaire", max_length=280, blank=True
    )
    beneficiary_availability = models.DateField(
        verbose_name="Disponibilité bénéficiaire", blank=True, null=True
    )

    beneficiary_attachments = ArrayField(
        models.CharField(max_length=1024),
        verbose_name="Documents joints",
        blank=True,
        default=list,
    )

    # Infos du référent
    referent_last_name = models.CharField(
        max_length=140, verbose_name="Nom référent", blank=True
    )
    referent_first_name = models.CharField(
        max_length=140, verbose_name="Prénom référent", blank=True
    )
    referent_phone = models.CharField(
        verbose_name="Tel référent", max_length=10, blank=True
    )
    referent_email = models.EmailField(verbose_name="Courriel référent", blank=True)

    # Meta
    prescriber = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Préscripteur",
        on_delete=models.SET_NULL,
        null=True,
    )
    prescriber_structure = models.ForeignKey(
        Structure,
        verbose_name="Structure",
        on_delete=models.CASCADE,
        db_index=True,
        related_name="+",
    )
    service = models.ForeignKey(
        Service,
        verbose_name="Service",
        on_delete=models.CASCADE,
        db_index=True,
        related_name="+",
    )
    orientation_reasons = models.TextField(
        verbose_name="Motif de l'orientation", blank=True
    )
    creation_date = models.DateTimeField(auto_now_add=True)
    processing_date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(
        max_length=10,
        choices=OrientationStatus.choices,
        default="ouverte",
    )

    def __str__(self):
        return f"Orientation #{self.id}"

    def get_magic_link(self):
        return self.get_frontend_url()

    def get_absolute_url(self):
        return self.get_frontend_url()

    def get_frontend_url(self):
        return f"{settings.FRONTEND_URL}/orientation/{self.query_id}"

    def get_beneficiary_full_name(self):
        if self.beneficiary_first_name or self.beneficiary_last_name:
            full_name = "%s %s" % (
                self.beneficiary_first_name,
                self.beneficiary_last_name,
            )
            return full_name.strip()
        return self.beneficiary_email

    def get_referent_full_name(self):
        if self.referent_first_name or self.referent_last_name:
            full_name = "%s %s" % (
                self.referent_first_name,
                self.referent_last_name,
            )
            return full_name.strip()
        return self.referent_email
