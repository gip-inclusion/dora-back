# Inspired from https://docs.djangoproject.com/en/3.2/topics/auth/customizing/#a-full-example
import logging

import sib_api_v3_sdk
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils import timezone
from sib_api_v3_sdk.rest import ApiException as SibApiException

logger = logging.getLogger(__name__)

MAIN_ACTIVITY_CHOICES = [
    ("accompagnateur", "Accompagnateur"),
    ("offreur", "Offreur"),
    ("accompagnateur_offreur", "Accompagnateur et offreur"),
    ("autre", "Autre"),
]

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
    department = models.CharField(
        max_length=3, default="", blank=True, help_text="Département d'un gestionnaire"
    )
    main_activity = models.CharField(
        max_length=25,
        choices=MAIN_ACTIVITY_CHOICES,
        verbose_name="Activité principale de l'utilisateur",
        db_index=True,
        blank=True,
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

    def start_onboarding(self, structure, is_first_admin):
        if settings.SIB_ACTIVE:
            admin_contact = structure.get_most_recently_active_admin()
            # Configure API key authorization: api-key
            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key["api-key"] = settings.SIB_API_KEY

            # create an instance of the API class
            api_instance = sib_api_v3_sdk.ContactsApi(
                sib_api_v3_sdk.ApiClient(configuration)
            )
            attributes = {
                "PRENOM": self.first_name,
                "NOM": self.last_name,
                "PROFIL": self.main_activity,
                "IS_ADMIN": structure.is_admin(self),
                "IS_FIRST_ADMIN": is_first_admin,
                "URL_DORA_STRUCTURE": structure.get_frontend_url(),
                "NEED_VALIDATION": structure.is_pending_member(self),
                "CONTACT_ADHESION": admin_contact.user.get_safe_name()
                if admin_contact and not is_first_admin
                else "",
            }
            create_contact = sib_api_v3_sdk.CreateContact(
                email=self.email,
                attributes=attributes,
                list_ids=[int(settings.SIB_ONBOARDING_LIST)],
                update_enabled=False,
            )

            try:
                # Create a contact
                api_response = api_instance.create_contact(create_contact)
                logger.info("User %s added to SiB: %s", self.pk, api_response)
            except SibApiException as e:
                # FIXME: l'API SIB / Brevo semble être un peu sensible sur l'inscription de contact
                # pour résoudre certains problèmes de rejets (HTTP 400), on loggue un peu plus profondément
                # pour investigation
                logger.error("SiB error details: UID=%s, email=%s, attrs=%s", self.pk, self.email, attributes)
                if create_contact:
                    logger.error("SiB Contact obj: %s", create_contact.to_dict())

                # les traces de l'exception peuvent être tronquées sur Sentry
                logger.exception(e)
