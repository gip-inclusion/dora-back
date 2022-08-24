from django.conf import settings
from django.template.loader import render_to_string

from dora.core.emails import send_mail


def send_services_update_email(emails, services):
    params = {
        "services": services,
        "homepage_url": settings.FRONTEND_URL,
    }
    body = render_to_string("service-update.html", params)

    send_mail(
        "[DORA] Actualisation de services",
        emails,
        body,
        tags=["service-update-notification"],
    )


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
    print(body)

    send_mail(
        f"[{settings.ENVIRONMENT}] Suggestion d'amélioration de service",
        settings.SUPPORT_EMAIL,
        body,
        tags=["feedback"],
    )
