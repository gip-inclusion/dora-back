from django.conf import settings
from django.template.loader import render_to_string

from dora.core.emails import send_mail


def send_password_reset_email(recipient_email, recipient_name, token):
    params = {
        "recipient_email": recipient_email,
        "recipient_name": recipient_name,
        "password_change_url": f"{settings.FRONTEND_URL}/auth/reinitialiser-mdp?token={token}",
        "homepage_url": settings.FRONTEND_URL,
    }
    txt_msg = render_to_string("pw-reset.txt", params)
    html_msg = render_to_string("pw-reset.html", params)

    send_mail(
        "[DORA] Votre demande de reinitialisation de mot de passe",
        recipient_email,
        txt_msg,
        html_content=html_msg,
        tags=["password_reset"],
    )


def send_email_validation_email(recipient_email, recipient_name, token):
    params = {
        "recipient_email": recipient_email,
        "recipient_name": recipient_name,
        "email_validation_url": f"{settings.FRONTEND_URL}/auth/validation-email?token={token}",
        "homepage_url": settings.FRONTEND_URL,
    }
    txt_msg = render_to_string("email-validation.txt", params)
    html_msg = render_to_string("email-validation.html", params)

    send_mail(
        "[DORA] Validation de votre compte DORA",
        recipient_email,
        txt_msg,
        html_content=html_msg,
        tags=["email_validation"],
    )
