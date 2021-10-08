import json

from django.conf import settings
from django.core.mail import EmailMultiAlternatives


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
