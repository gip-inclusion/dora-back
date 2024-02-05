from django.conf import settings
from django.template.loader import render_to_string
from django.utils.encoding import iri_to_uri
from furl import furl
from mjml import mjml2html

from dora.core.emails import send_mail


def send_invitation_reminder(user, structure):
    cta_link = furl(settings.FRONTEND_URL) / "auth" / "invitation"
    cta_link.add({"login_hint": iri_to_uri(user.email), "structure": structure.slug})
    context = {
        "user": user,
        "structure": structure,
        "cta_link": cta_link.url,
        "with_dora_info": True,
        "with_legal_info": True,
    }

    send_mail(
        f"Rappel : Acceptez l'invitation à rejoindre {structure.name} sur DORA",
        user.email,
        mjml2html(render_to_string("invitation_reminder.mjml", context)),
    )
