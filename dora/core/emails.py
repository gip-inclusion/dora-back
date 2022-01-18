import json

from django.conf import settings
from django.core.mail import EmailMessage


def send_mail(
    subject,
    to,
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
    msg = EmailMessage(
        subject,
        body,
        from_email,
        [to],
        headers=headers,
        reply_to=reply_to,
    )
    msg.content_subtype = "html"
    msg.send()
