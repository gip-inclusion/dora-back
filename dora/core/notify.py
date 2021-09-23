import json

import requests
from django.conf import settings


def send_mattermost_notification(msg):
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
