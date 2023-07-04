import datetime
import json

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from furl import furl


def send_mail(
    subject,
    to,  # string ou tableau de string
    body,
    from_email=settings.DEFAULT_FROM_EMAIL,
    tags=None,
    reply_to=None,
):
    headers = {
        "X-TM-DOMAIN": settings.EMAIL_DOMAIN,
        "X-TM-TAGS": json.dumps(tags) if tags else "",
        "X-TM-TRACKING": '{"html":{"open":0,"click":0,"text":{"click":0}}}',
        "X-TM-GOOGLEANALYTICS": '{"enable":"0"}',
        "X-TM-TEXTVERSION": 1,
    }

    # Conversion en liste si besoin
    if not isinstance(to, list):
        to = [to]

    msg = EmailMessage(
        subject,
        body,
        from_email,
        to,
        headers=headers,
        reply_to=reply_to,
    )
    msg.content_subtype = "html"
    msg.send()


def send_services_check_email(
    recipient_email, recipient_name, structures_to_update, structures_with_drafts
):
    today = datetime.date.today()
    for structure in structures_to_update:
        utms = f"utm_source=NotifTransacDora&utm_medium=email&utm_campaign=Actualisation-{today.year}-{today.month:02}"
        redirect = f"/structures/{structure.slug}/services?update-status=ALL&{utms}"
        structure.link = furl(settings.FRONTEND_URL).add(
            path="/auth/connexion",
            args={
                "next": redirect,
            },
        )
    for structure in structures_with_drafts:
        utms = f"utm_source=NotifTransacDora&utm_medium=email&utm_campaign=Brouillon-{today.year}-{today.month:02}"
        redirect = f"/structures/{structure.slug}/services?service-status=DRAFT&{utms}"
        structure.link = furl(settings.FRONTEND_URL).add(
            path="/auth/connexion",
            args={
                "next": redirect,
            },
        )

    params = {
        "recipient_email": recipient_email,
        "recipient_name": recipient_name,
        "structures_to_update": structures_to_update,
        "structures_with_drafts": structures_with_drafts,
        "homepage_url": settings.FRONTEND_URL,
    }
    body = render_to_string("email_services_check.html", params)
    send_mail(
        "Des mises à jour de votre offre de service sur DORA sont nécessaires",
        recipient_email,
        body,
        tags=["services_check"],
    )
