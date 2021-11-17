import textwrap

from django.conf import settings

from dora.core.emails import send_mail


def send_service_feedback_email(service, full_name, email, message):
    txt_msg = (
        textwrap.dedent(
            f"""
        Suggestion d’amélioration envoyée par {full_name} ({email}) pour le service:
        “{service.name}” de la structure “{service.structure.name} ({service.structure.department})”
        {settings.FRONTEND_URL}/services/{service.slug}
        Le contact du service est {service.contact_name} ({service.contact_email} {service.contact_phone})
        Le contact de la structure est {service.structure.email}
        -----
        """
        ).strip()
        + f"\n\n{message}"
    )

    send_mail(
        f"[{settings.ENVIRONMENT}] Suggestion d'amelioration de service",
        settings.SUPPORT_EMAIL,
        txt_msg,
        tags=["feedback"],
    )
