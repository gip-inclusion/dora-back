import datetime
import json

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from furl import furl


def clean_reply_to(emails):
    # Déduplique et enlève les adresses vides
    if emails:
        return list(set(email for email in emails if email))


def send_mail(
    subject,
    # chaine ou liste de chaines
    to,
    body,
    # soit une chaine, soit un tuple (nom, email)
    from_email=("La plateforme DORA", settings.DEFAULT_FROM_EMAIL),
    tags=None,
    reply_to=None,
    attachments=None,
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

    if type(from_email) in [list, tuple]:
        name = from_email[0].replace('"', r"\"")
        email = from_email[1]
        from_email = f'"{name}" <{email}>'

    msg = EmailMessage(
        subject,
        body,
        from_email,
        to,
        headers=headers,
        reply_to=clean_reply_to(reply_to),
    )
    msg.content_subtype = "html"
    if attachments is not None:
        for attachment in attachments:
            filename = attachment.split("/")[-1]
            msg.attach(
                filename,
                default_storage.open(attachment).read(),
            )
    msg.send()
    if attachments is not None:
        for attachment in attachments:
            default_storage.delete(attachment)


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
