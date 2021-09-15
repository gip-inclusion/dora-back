import os

from django.conf import settings
from django.core.mail import send_mail


def send_password_reset_email(email, token):
    chg_pw_url = f"{os.environ['FRONTEND_URL']}/auth/password-reset/?token={token}"
    send_mail(
        subject="[DORA] Votre demande de réinitialisation de mot de passe",
        message=f"{chg_pw_url}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )
