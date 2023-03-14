# Inspired from https://docs.djangoproject.com/en/3.2/topics/auth/customizing/#a-full-example

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils import timezone

from dora.core.utils import add_to_sib


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
    phone_number = models.CharField(max_length=10, blank=True)

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
    department = models.CharField(
        max_length=3, default="", blank=True, help_text="Département d'un gestionnaire"
    )

    date_joined = models.DateTimeField("date joined", default=timezone.now)
    last_notification_email_sent = models.DateTimeField(blank=True, null=True)
    newsletter = models.BooleanField(default=False, db_index=True)

    bookmarks = models.ManyToManyField("services.Service", through="services.Bookmark")
    onboarding_actions_accomplished = models.JSONField(default=dict)

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

    def start_onboarding(self):
        add_to_sib(self)
