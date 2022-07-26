import json

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string


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

    # Conversion en list si besoin
    if not isinstance(to, list):
        to = [to]

    if settings.FAKE_EMAIL_RECIPIENT and not settings.IS_TESTING:
        subject = f"[TEST pour {to.join(', ')}] {subject}"
        to = settings.FAKE_EMAIL_RECIPIENT

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


def send_draft_reminder_email(recipient_email, recipient_name, structure, drafts):
    params = {
        "recipient_email": recipient_email,
        "recipient_name": recipient_name,
        "drafts": drafts,
        "structure": structure,
        "homepage_url": settings.FRONTEND_URL,
    }
    body = render_to_string("email_drafts.html", params)
    send_mail(
        "[DORA] Besoin d'aide ?",
        recipient_email,
        body,
        tags=["draft_notif"],
    )
