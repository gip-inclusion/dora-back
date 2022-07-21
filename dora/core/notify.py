import json

import requests
from django.conf import settings

from dora.core.emails import send_mail


def send_mattermost_notification(msg):
    if settings.ENVIRONMENT == "local":
        if not settings.IS_TESTING:
            print("Mattermost notification: ", msg)
    else:
        try:
            if settings.MATTERMOST_HOOK_KEY:
                requests.post(
                    url=f"https://mattermost.incubateur.net/hooks/{settings.MATTERMOST_HOOK_KEY}",
                    headers={
                        "Content-Type": "application/json",
                    },
                    data=json.dumps({"text": msg}),
                )

        except requests.exceptions.RequestException:
            # TODO: logging
            print("HTTP Request failed")


def send_moderation_email(subject, msg):
    body = f"<html><body>{msg}</body>"
    if settings.MODERATION_EMAIL_ADRESS:
        send_mail(subject, settings.MODERATION_EMAIL_ADRESS, msg, tags=["moderation"])
    elif not settings.IS_TESTING:
        print("Moderation email:", subject, body)
