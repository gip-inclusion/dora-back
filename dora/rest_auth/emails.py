import json

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def send_mail(
    subject,
    to,
    text_content,
    html_content=None,
    from_email=settings.DEFAULT_FROM_EMAIL,
    tags=None,
    reply_to=None,
):
    headers = {
        "X-TM-DOMAIN": settings.EMAIL_DOMAIN,
        "X-TM-TAGS": json.dumps(tags) if tags else "",
        "X-TM-TRACKING": '{"html":{"open":0,"click":0,"text":{"click":0}}}',
        "X-TM-GOOGLEANALYTICS": '{"enable":"0"}',
    }
    msg = EmailMultiAlternatives(
        subject,
        text_content,
        from_email,
        [to],
        headers=headers,
        reply_to=reply_to,
    )
    if html_content:
        msg.attach_alternative(html_content, "text/html"),
    msg.send()


def send_password_reset_email(recipient_email, recipient_name, token):
    params = {
        "recipient_email": recipient_email,
        "recipient_name": recipient_name,
        "password_change_url": f"{settings.FRONTEND_URL}/auth/reinitialiser-mdp/?token={token}",
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
        "email_validation_url": f"{settings.FRONTEND_URL}/auth/validation-email/?token={token}",
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
