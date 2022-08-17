import json

import requests
from django.conf import settings
from django.utils import timezone


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


def send_moderation_notification(entity, user, msg, new_status):
    if new_status != entity.moderation_status:
        msg += f"\nNouveau statut de modération : {new_status.label}"
    entity.log_note(user, msg)
    entity.moderation_status = new_status
    entity.moderation_date = timezone.now()
    entity.save()
