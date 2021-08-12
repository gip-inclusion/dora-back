import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.crypto import get_random_string
from django.utils.text import slugify


# From: https://github.com/betagouv/itou/blob/master/itou/utils/validators.py
def validate_siret(siret):
    if not siret.isdigit() or len(siret) != 14:
        raise ValidationError("Le numéro SIRET doit être composé de 14 chiffres.")


def make_unique_slug(instance, value, length=20):
    model = instance.__class__
    base_slug = slugify(value)[:length]
    unique_slug = base_slug
    while model.objects.filter(slug=unique_slug).exists():
        unique_slug = (
            base_slug + "-" + get_random_string(4, "abcdefghijklmnopqrstuvwxyz")
        )
    return unique_slug


class Structure(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    siret = models.CharField(
        verbose_name="Siret",
        max_length=14,
        validators=[validate_siret],
    )
    slug = models.SlugField(blank=True)
    name = models.CharField(verbose_name="Nom", max_length=255)
    short_desc = models.TextField(blank=True)
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
    postal_code = models.CharField(max_length=5, blank=True)
    city_code = models.CharField(max_length=5, blank=True)
    city = models.CharField(max_length=255, blank=True)
    address1 = models.CharField(max_length=255, blank=True)
    address2 = models.CharField(max_length=255, blank=True)
    has_services = models.BooleanField(default=False, blank=True)
    ape = models.CharField(max_length=6, blank=True)
    longitude = models.FloatField(blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)

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

    # TODO: opening_hours, edit history, moderation

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = make_unique_slug(self, self.name)
        return super().save(*args, **kwargs)
