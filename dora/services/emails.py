import datetime

from django.conf import settings
from django.template.loader import render_to_string
from furl import furl

from dora.core.emails import send_mail


def send_service_feedback_email(service, full_name, email, message):
    html_message = message.replace("\n", "<br>")
    body = f"""
        <html><body>
        Suggestion d’amélioration envoyée par {full_name} ({email}) pour le service:<br>
        “<a href="{settings.FRONTEND_URL}/services/{service.slug}">{service.name}</a>” de la structure<br>
        “<a href="{settings.FRONTEND_URL}/structures/{service.structure.slug}">{service.structure.name}</a> ({service.structure.department})”<br>

        Le contact du service est {service.contact_name} ({service.contact_email} {service.contact_phone})<br>
        Le contact de la structure est <a href="mailto:{service.structure.email}">{service.structure.email}</a><br>
        <hr><br><br>
        {html_message}
        </body>
        """

    send_mail(
        f"[{settings.ENVIRONMENT}] Suggestion d'amélioration de service",
        settings.SUPPORT_EMAIL,
        body,
        tags=["feedback"],
    )


def send_service_reminder_email(
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
    }
    body = render_to_string("email_services_check.html", params)
    send_mail(
        "Des mises à jour de votre offre de service sur DORA sont nécessaires",
        recipient_email,
        body,
        tags=["services_check"],
    )
