import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.crypto import get_random_string
from django.utils.text import slugify

from dora.sirene.serializers import EstablishmentSerializer
from dora.structures.emails import (
    send_access_granted_notification,
    send_access_rejected_notification,
    send_access_requested_notification,
    send_invitation_accepted_notification,
)
from dora.users.models import User


# From: https://github.com/betagouv/itou/blob/master/itou/utils/validators.py
def validate_siret(siret):
    if not siret.isdigit() or len(siret) != 14:
        raise ValidationError("Le numéro SIRET doit être composé de 14 chiffres.")


def validate_safir(safir):
    if not safir.isdigit() or len(safir) != 5:
        raise ValidationError("Le code SAFIR doit être composé de 14 chiffres.")


def make_unique_slug(instance, value, length=20):
    model = instance.__class__
    base_slug = slugify(value)[:length]
    unique_slug = base_slug
    while model.objects.filter(slug=unique_slug).exists():
        unique_slug = (
            base_slug + "-" + get_random_string(4, "abcdefghijklmnopqrstuvwxyz")
        )
    return unique_slug


class StructurePutativeMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="putative_membership",
    )
    structure = models.ForeignKey(
        "Structure", on_delete=models.CASCADE, related_name="putative_membership"
    )
    will_be_admin = models.BooleanField(default=False)
    creation_date = models.DateTimeField(auto_now_add=True)

    invited_by_admin = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Membre Potentiel"
        verbose_name_plural = "Membres Potentiels"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "structure"],
                name="%(app_label)s_unique_putative_member_by_structure",
            )
        ]

    def notify_admin_access_requested(self):
        structure_admins = StructureMember.objects.filter(
            structure=self.structure, is_admin=True
        ).exclude(user=self.user)
        for admin in structure_admins:
            send_access_requested_notification(self, admin.user)

    def notify_access_rejected(self):
        send_access_rejected_notification(self)


class StructureMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="membership"
    )
    structure = models.ForeignKey(
        "Structure", on_delete=models.CASCADE, related_name="membership"
    )
    is_admin = models.BooleanField(default=False)
    # has_accepted_invitation = models.BooleanField(default=False)

    creation_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Membre"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "structure"],
                name="%(app_label)s_unique_user_by_structure",
            )
        ]

    def notify_admins_invitation_accepted(self):
        structure_admins = StructureMember.objects.filter(
            structure=self.structure, is_admin=True
        ).exclude(user=self.user)
        for admin in structure_admins:
            send_invitation_accepted_notification(self, admin.user)

    def notify_access_granted(self):
        send_access_granted_notification(self)


class StructureSource(models.TextChoices):
    DORA_STAFF = "DORA", "Équipe DORA"
    ITOU = "ITOU", "Import ITOU"
    STRUCT_STAFF = "PORTEUR", "Porteur"
    PE_API = "PE", "API Référentiel Agence PE"
    BATCH_INVITE = "BI", "Invitations en masse"


class StructureTypology(models.TextChoices):
    # https://docs.google.com/spreadsheets/d/1scfJUEcNWP9KMrHFf_7OCCSs4RyDZmH3dK70HJA-rIk/
    AC = "AC", "Associations de chômeurs"
    ACI = "ACI", "Structures porteuses d’ateliers et chantiers d’insertion (ACI)"
    ACIPHC = (
        "ACIPHC",
        "SIAE — Atelier chantier d’insertion premières heures en chantier",
    )
    AFPA = (
        "AFPA",
        "Agence nationale pour la formation professionnelle des adultes (AFPA)",
    )
    AI = "AI", "Associations intermédiaires (AI)"
    ASE = "ASE", "Aide sociale à l’enfance (ASE)"
    ASSO = "ASSO", "Associations"
    CADA = "CADA", "Centres d’accueil de demandeurs d’asile (CADA)"
    CAF = "CAF", "Caisses d’allocation familiale (CAF)"
    CAP_EMPLOI = "CAP_EMPLOI", "Cap Emploi"
    CAVA = "CAVA", "Centres d’adaptation à la vie active (CAVA)"
    CC = "CC", "Communautés de Commune"
    CCAS = "CCAS", "Centres communaux d’action sociale (CCAS)"
    CD = "CD", "Conseils Départementaux (CD)"
    CHRS = "CHRS", "Centres d’hébergement et de réinsertion sociale (CHRS)"
    CHU = "CHU", "Centres d’hébergement d’urgence (CHU)"
    CIAS = "CIAS", "Centres intercommunaux d’action sociale (CIAS)"
    CIDFF = (
        "CIDFF",
        "Centres d’information sur les droits des femmes et des familles (CIDFF)",
    )
    CPH = "CPH", "Centres provisoires d’hébergement (CPH)"
    CS = "CS", "Centre social"
    CT = "CT", "Collectivités territoriales"
    DEETS = (
        "DEETS",
        "Directions de l’Economie, de l’Emploi, du Travail et des Solidarités (DEETS)",
    )
    DIPLP = (
        "DIPLP",
        "Délégation interministérielles à la prévention et à la lutte contre la pauvreté",
    )
    EA = "EA", "Entreprise adaptée (EA)"
    EATT = "EATT", "Entreprise Adaptée (EATT)"
    EI = "EI", "Entreprises d’insertion (EI)"
    EITI = "EITI", "Entreprises d’insertion par le travail indépendant (EITI)"
    EPCI = "EPCI", "Intercommunalité (EPCI)"
    ETTI = "ETTI", "Entreprises de travail temporaire d’insertion (ETTI)"
    FAIS = "FAIS", "Fédérations d’acteurs de l’insertion et de la solidarité"
    GEIQ = (
        "GEIQ",
        "Groupements d’employeurs pour l’insertion et la qualification (GEIQ)",
    )
    ML = "ML", "Mission Locale"
    MQ = "MQ", "Maison de quartier"
    MSA = "MSA", "Mutualité Sociale Agricole"
    MSAP = "MSAP", "Maison de Service au Public (MSAP)"
    MUNI = "MUNI", "Municipalités"
    OACAS = (
        "OACAS",
        "Structures agréées Organisme d’accueil communautaire et d’activité solidaire (OACAS)",
    )
    OF = "OF", "Organisme de formations"
    OTHER = "OTHER", "Autre"
    PE = "PE", "Pôle emploi"
    PIJ_BIJ = "PIJ_BIJ", "Points et bureaux information jeunesse (PIJ/BIJ)"
    PIMMS = "PIMMS", "Point Information Médiation Multi Services (PIMMS)"
    PJJ = "PJJ", "Protection judiciaire de la jeunesse (PJJ)"
    PLIE = "PLIE", "Plans locaux pour l’insertion et l’emploi (PLIE)"
    PR = "PR", "Préfecture, Sous-Préfecture"
    RE = "RE", "Région"
    SCCD = "SCCD", "Services sociaux du Conseil départemental"
    SCP = "SCP", "Services et clubs de prévention"
    SPIP = "SPIP", "Services pénitentiaires d’insertion et de probation (SPIP)"
    TL = "TL", "Tiers lieu & coworking"
    UDAF = "UDAF", "Union Départementale d’Aide aux Familles (UDAF)"


class StructureManager(models.Manager):
    def create_from_establishment(self, establishment):
        data = EstablishmentSerializer(establishment).data
        structure = self.model(
            siret=data["siret"],
            name=data["name"],
            address1=data["address1"],
            address2=data["address2"],
            postal_code=data["postal_code"],
            city_code=data["city_code"],
            city=data["city"],
            ape=data["ape"],
            longitude=data["longitude"],
            latitude=data["latitude"],
        )
        structure.save()
        return structure


class Structure(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    siret = models.CharField(
        verbose_name="Siret", max_length=14, validators=[validate_siret], unique=True
    )
    code_safir_pe = models.CharField(
        verbose_name="Code Safir Pole Emploi",
        max_length=5,
        validators=[validate_safir],
        unique=True,
        null=True,
        blank=True,
        db_index=True,
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
    email = models.EmailField(blank=True)
    postal_code = models.CharField(
        max_length=5,
    )
    city_code = models.CharField(max_length=5, blank=True)
    city = models.CharField(max_length=255)
    department = models.CharField(max_length=3, blank=True)
    address1 = models.CharField(max_length=255)
    address2 = models.CharField(max_length=255, blank=True)
    has_services = models.BooleanField(default=False, blank=True)
    ape = models.CharField(max_length=6, blank=True)
    longitude = models.FloatField(blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)

    creation_date = models.DateTimeField(auto_now_add=True)
    modification_date = models.DateTimeField(auto_now=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="+",
    )
    last_editor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
    )

    source = models.CharField(
        max_length=12,
        choices=StructureSource.choices,
        blank=True,
        db_index=True,
    )

    members = models.ManyToManyField(User, through=StructureMember)

    is_antenna = models.BooleanField(default=False, db_index=True)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, blank=True, null=True)
    objects = StructureManager()

    # TODO: opening_hours, edit history, moderation

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = make_unique_slug(self, self.name)
        if not self.department and self.city_code:
            code = self.city_code
            self.department = code[:3] if code.startswith("97") else code[:2]
        return super().save(*args, **kwargs)

    def can_write(self, user):
        return (
            user.is_staff
            or StructureMember.objects.filter(
                structure_id=self.id, user_id=user.id
            ).exists()
        )
