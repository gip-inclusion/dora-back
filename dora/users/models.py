# Inspired from https://docs.djangoproject.com/en/3.2/topics/auth/customizing/#a-full-example
import logging

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone

from .enums import DiscoveryMethod, MainActivity

logger = logging.getLogger(__name__)

IC_PRODUCTION_DATE = timezone.make_aware(timezone.datetime(2022, 10, 3))


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError("Users must have an email address")

        user = self.model(email=self.normalize_email(email), **extra_fields)

        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Creates and saves a superuser with the given email and password.
        """
        user = self.create_user(email, password=password, **extra_fields)
        user.is_staff = True
        user.save()
        return user

    def get_dora_bot(self):
        return self.get(email=settings.DORA_BOT_USER)

    def orphans(self):
        # utilisateurs sans structure et sans invitation
        return self.filter(putative_membership=None, membership=None, is_staff=False)

    def to_delete(self):
        return self.filter(putative_membership=None).filter(
            # non validés avant IC
            models.Q(is_valid=False, date_joined__lt=IC_PRODUCTION_DATE)
            # non validés et sans identifiant IC
            | models.Q(is_valid=False, ic_id=None)
        )

    def members_invited(self):
        # invités par un admin de structure, en attente
        return (
            self.exclude(putative_membership=None)
            .filter(putative_membership__invited_by_admin=True)
            .prefetch_related("putative_membership")
        )


class User(AbstractBaseUser):
    ic_id = models.UUIDField(
        verbose_name="Identifiant Inclusion Connect", null=True, blank=True
    )
    email = models.EmailField(
        verbose_name="email address",
        max_length=255,
        unique=True,
    )
    last_name = models.CharField("Nom de famille", max_length=140, blank=True)
    first_name = models.CharField("Prénom", max_length=140, blank=True)

    is_active = models.BooleanField(
        "active",
        default=True,
        help_text=(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    is_valid = models.BooleanField(
        "valid",
        default=False,
        help_text="Designates whether this user's email address has been validated.",
    )
    is_staff = models.BooleanField(
        "staff status",
        default=False,
        help_text="Designates whether the user can log into this admin site.",
    )
    is_manager = models.BooleanField(
        "gestionnaire",
        default=False,
        help_text="Indique si l’utilisateur est un gestionnaire (de département)",
    )
    departments = ArrayField(
        base_field=models.CharField(
            max_length=3,
        ),
        blank=True,
        null=True,
        verbose_name="Départements en gestion",
        help_text="Liste des numéros des départements gérés par l'utilisateur (s’il est gestionnaire). Séparés par des virgules.",
    )
    main_activity = models.CharField(
        max_length=25,
        choices=MainActivity.choices,
        verbose_name="Activité principale de l'utilisateur",
        db_index=True,
        blank=True,
    )
    discovery_method = models.CharField(
        max_length=25,
        choices=DiscoveryMethod.choices,
        verbose_name="comment avez-vous connu DORA ?",
        blank=True,
        null=True,
    )
    discovery_method_other = models.CharField(
        max_length=255,
        verbose_name="comment avez-vous connu DORA ? (autre)",
        blank=True,
        null=True,
    )
    date_joined = models.DateTimeField("date joined", default=timezone.now)
    last_service_reminder_email_sent = models.DateTimeField(blank=True, null=True)
    newsletter = models.BooleanField(default=False, db_index=True)

    bookmarks = models.ManyToManyField("services.Service", through="services.Bookmark")

    cgu_versions_accepted = models.JSONField(default=dict)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"
        abstract = False

    def __str__(self):
        return self.email

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True

    def get_full_name(self):
        if self.first_name or self.last_name:
            full_name = "%s %s" % (self.first_name, self.last_name)
            return full_name.strip()
        return self.email

    def get_short_name(self):
        return self.first_name or self.last_name or self.email

    def get_safe_name(self):
        # Masque le prénom
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}. {self.last_name}"
        return self.email.split("@")[0]
