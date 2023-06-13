import binascii
import os

from django.conf import settings
from django.db import models
from rest_framework.authtoken.models import Token as DRFToken


class Token(DRFToken):
    # Based on rest_framework.authtoken.models.Token
    # but expirable, and allow more than one per user

    key = models.CharField("Key", max_length=40, primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="auth_token",
        on_delete=models.CASCADE,
        verbose_name="User",
    )
    created = models.DateTimeField("Created", auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super().save(*args, **kwargs)

    @classmethod
    def generate_key(cls):
        return binascii.hexlify(os.urandom(20)).decode()

    def __str__(self):
        return self.key
