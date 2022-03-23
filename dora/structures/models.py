import uuid

from django.conf import settings
from django.db import models
from django.db.models import CharField, Q
from django.db.models.functions import Length
from django.utils.crypto import get_random_string
from django.utils.text import slugify

from dora.core.models import EnumModel
from dora.core.utils import code_insee_to_code_dept
from dora.core.validators import validate_safir, validate_siret
from dora.sirene.serializers import EstablishmentSerializer
from dora.structures.emails import (
    send_access_granted_notification,
    send_access_rejected_notification,
    send_access_requested_notification,
    send_invitation_accepted_notification,
)
from dora.users.models import User

CharField.register_lookup(Length)


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
    is_admin = models.BooleanField(default=False)
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


class StructureSource(EnumModel):
    class Meta:
        verbose_name = "Source"


class StructureTypology(EnumModel):
    class Meta:
        verbose_name = "Typologie"


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

    def create_from_parent_structure(self, parent, **kwargs):
        structure = self.model(
            siret=None,
            parent=parent,
            branch_id=get_random_string(5, "abcdefghijklmnopqrstuvwxyz"),
            **kwargs,
        )
        structure.save()
        return structure


class Structure(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Les antennes peuvent avoir un Siret null
    siret = models.CharField(
        verbose_name="Siret",
        max_length=14,
        validators=[validate_siret],
        null=True,
        unique=True,
    )
    branch_id = models.CharField(max_length=5, blank=True, default="")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, blank=True, null=True)

    code_safir_pe = models.CharField(
        verbose_name="Code Safir Pole Emploi",
        max_length=5,
        validators=[validate_safir],
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )

    typology = models.ForeignKey(
        StructureTypology, null=True, blank=True, on_delete=models.PROTECT
    )

    slug = models.SlugField(blank=True, null=True, unique=True)
    name = models.CharField(verbose_name="Nom", max_length=255)
    short_desc = models.CharField(max_length=280)
    url = models.URLField(blank=True)
    full_desc = models.TextField(blank=True)
    phone = models.CharField(max_length=10, blank=True)
    email = models.EmailField(blank=True)
    postal_code = models.CharField(
        max_length=5,
    )
    city_code = models.CharField(max_length=5, blank=True)
    city = models.CharField(max_length=255)
    department = models.CharField(max_length=3, blank=True)
    address1 = models.CharField(max_length=255)
    address2 = models.CharField(max_length=255, blank=True)
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

    source = models.ForeignKey(
        StructureSource, null=True, blank=True, on_delete=models.PROTECT
    )

    members = models.ManyToManyField(User, through=StructureMember)

    objects = StructureManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["branch_id", "parent"],
                name="%(app_label)s_%(class)s_unique_branch_by_parent",
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_valid_or_null_siren",
                check=Q(siret__length=14) | Q(siret__isnull=True),
            ),
        ]

    # TODO: opening_hours, edit history, moderation

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = make_unique_slug(self, self.name)
        if not self.department and self.city_code:
            code = self.city_code
            self.department = code_insee_to_code_dept(code)
        return super().save(*args, **kwargs)

    def can_write(self, user):
        return (
            user.is_staff
            or StructureMember.objects.filter(
                structure_id=self.id, user_id=user.id
            ).exists()
        )
