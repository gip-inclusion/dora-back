from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
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


def send_account_deletion_notification(user):
    # envoyé 30j avant la destruction effective du compte utilisateur
    cta_link = furl(settings.FRONTEND_URL) / "auth" / "connexion"
    cta_link.add(
        {
            "login_hint": iri_to_uri(user.email),
            "mtm_campaign": "MailsTransactionnels",
            "mtm_kwd": "RelanceInactif",
        }
    )
    context = {
        "limit_date": timezone.localdate() + relativedelta(days=30),
        "cta_link": cta_link.url,
    }

    send_mail(
        "DORA - Suppression prochaine de votre compte",
        user.email,
        mjml2html(render_to_string("notification_account_deletion.mjml", context)),
    )
