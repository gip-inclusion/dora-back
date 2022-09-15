from django.conf import settings

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
