from django.conf import settings
from django.core.files.storage import default_storage
from django.template.loader import render_to_string
from mjml import mjml2html

from dora.core.emails import send_mail
from dora.orientations.models import ContactPreference


def send_orientation_created_emails(orientation):
    beneficiaries_contact_methods = [
        method
        for method in [
            orientation.beneficiary_phone,
            orientation.beneficiary_email,
            orientation.beneficiary_other_contact_method,
        ]
        if method
    ]

    context = {
        "data": orientation,
        "homepage_url": settings.FRONTEND_URL,
        "ContactPreference": ContactPreference,
        "support_email": settings.SUPPORT_EMAIL,
        "support_link": settings.ORIENTATION_SUPPORT_LINK,
        "beneficiaries_has_alternate_contact_methods": len(
            beneficiaries_contact_methods
        )
        > len(orientation.beneficiary_contact_preferences),
        "attachments": [
            {"name": a, "url": default_storage.url(a)}
            for a in orientation.beneficiary_attachments
        ],
    }
    # Structure porteuse
    send_mail(
        f"{'[Envoyée - Structure porteuse] ' if settings.ORIENTATION_EMAILS_DEBUG else''}Nouvelle demande d’orientation reçue",
        orientation.service.contact_email,
        mjml2html(render_to_string("orientation-created-structure.mjml", context)),
        from_email=(
            f"{orientation.prescriber.get_full_name()} via DORA",
            settings.DEFAULT_FROM_EMAIL,
        ),
        tags=["orientation"],
        reply_to=[orientation.prescriber.email],
    )
    # Prescripteur
    send_mail(
        f"{'[Envoyée - Prescripteur] ' if settings.ORIENTATION_EMAILS_DEBUG else''}Votre demande a bien été transmise !",
        orientation.prescriber.email,
        mjml2html(render_to_string("orientation-created-prescriber.mjml", context)),
        tags=["orientation"],
        reply_to=[orientation.service.contact_email],
    )
    # Référent
    if (
        orientation.referent_email
        and orientation.referent_email != orientation.prescriber.email
    ):
        send_mail(
            f"{'[Envoyée - Conseiller référent] ' if settings.ORIENTATION_EMAILS_DEBUG else''}Notification d’une demande d’orientation",
            orientation.referent_email,
            mjml2html(render_to_string("orientation-created-referent.mjml", context)),
            tags=["orientation"],
            reply_to=[orientation.prescriber.email],
        )
    # Bénéficiaire
    if orientation.beneficiary_email:
        send_mail(
            f"{'[Envoyée - Bénéficiaire] ' if settings.ORIENTATION_EMAILS_DEBUG else''}Une orientation a été effectuée en votre nom",
            orientation.beneficiary_email,
            mjml2html(
                render_to_string("orientation-created-beneficiary.mjml", context)
            ),
            from_email=(
                f"{orientation.prescriber.get_full_name()} via DORA",
                settings.DEFAULT_FROM_EMAIL,
            ),
            tags=["orientation"],
            reply_to=[orientation.prescriber.email],
        )


def send_orientation_accepted_emails(
    orientation, prescriber_message, beneficiary_message
):
    context = {
        "data": orientation,
        "homepage_url": settings.FRONTEND_URL,
        "support_email": settings.SUPPORT_EMAIL,
        "support_link": settings.ORIENTATION_SUPPORT_LINK,
        "prescriber_message": prescriber_message,
        "beneficiary_message": beneficiary_message,
    }

    # Structure
    send_mail(
        f"{'[Validée - Structure porteuse] ' if settings.ORIENTATION_EMAILS_DEBUG else''}Vous venez de valider une demande 🎉",
        [orientation.service.contact_email],
        mjml2html(render_to_string("orientation-accepted-structure.mjml", context)),
        tags=["orientation"],
    )

    # Prescripteur
    send_mail(
        f"{'[Validée - Prescripteur] ' if settings.ORIENTATION_EMAILS_DEBUG else''}Votre demande a été acceptée ! 🎉",
        orientation.prescriber.email,
        mjml2html(render_to_string("orientation-accepted-prescriber.mjml", context)),
        from_email=(
            f"{orientation.service.structure.name} via DORA",
            settings.DEFAULT_FROM_EMAIL,
        ),
        tags=["orientation"],
        reply_to=[orientation.service.contact_email],
    )
    # Référent
    if (
        orientation.referent_email
        and orientation.referent_email != orientation.prescriber.email
    ):
        send_mail(
            f"{'[Validée - Conseiller référent] ' if settings.ORIENTATION_EMAILS_DEBUG else''}Notification de l’acceptation d’une demande d’orientation",
            orientation.referent_email,
            mjml2html(render_to_string("orientation-accepted-referent.mjml", context)),
            from_email=(
                f"{orientation.service.structure.name} via DORA",
                settings.DEFAULT_FROM_EMAIL,
            ),
            tags=["orientation"],
            reply_to=[orientation.prescriber.email],
        )
    # Bénéficiaire
    if orientation.beneficiary_email:
        send_mail(
            f"{'[Validée - Bénéficiaire] ' if settings.ORIENTATION_EMAILS_DEBUG else''}Votre demande a été acceptée ! 🎉",
            orientation.beneficiary_email,
            mjml2html(
                render_to_string("orientation-accepted-beneficiary.mjml", context)
            ),
            from_email=(
                f"{orientation.service.structure.name} via DORA",
                settings.DEFAULT_FROM_EMAIL,
            ),
            tags=["orientation"],
            reply_to=[orientation.service.contact_email],
        )


def send_orientation_rejected_emails(orientation, message):
    context = {
        "data": orientation,
        "homepage_url": settings.FRONTEND_URL,
        "support_email": settings.SUPPORT_EMAIL,
        "support_link": settings.ORIENTATION_SUPPORT_LINK,
        "message": message,
    }

    # Structure
    send_mail(
        f"{'[Refusée - Structure porteuse] ' if settings.ORIENTATION_EMAILS_DEBUG else''}Vous venez de refuser une demande",
        [orientation.service.contact_email],
        mjml2html(render_to_string("orientation-rejected-structure.mjml", context)),
        tags=["orientation"],
    )

    # Prescripteur
    send_mail(
        f"{'[Refusée - Prescripteur] ' if settings.ORIENTATION_EMAILS_DEBUG else''}Votre demande d’orientation a été refusée",
        [orientation.prescriber.email],
        mjml2html(render_to_string("orientation-rejected-prescriber.mjml", context)),
        from_email=(
            f"{orientation.service.structure.name} via DORA",
            settings.DEFAULT_FROM_EMAIL,
        ),
        tags=["orientation"],
        reply_to=[orientation.service.contact_email],
    )

    if (
        orientation.referent_email
        and orientation.referent_email != orientation.prescriber.email
    ):
        # Referent
        send_mail(
            f"{'[Refusée - Conseiller référent] ' if settings.ORIENTATION_EMAILS_DEBUG else''}Votre demande d’orientation a été refusée",
            [orientation.referent_email],
            mjml2html(
                render_to_string("orientation-rejected-prescriber.mjml", context)
            ),
            from_email=(
                f"{orientation.service.structure.name} via DORA",
                settings.DEFAULT_FROM_EMAIL,
            ),
            tags=["orientation"],
            reply_to=[orientation.service.contact_email],
        )


def send_message_to_prescriber(orientation, message, cc):
    context = {
        "data": orientation,
        "homepage_url": settings.FRONTEND_URL,
        "message": message,
        "support_email": settings.SUPPORT_EMAIL,
        "support_link": settings.ORIENTATION_SUPPORT_LINK,
    }
    send_mail(
        f"{'[Contact - Prescripteur] ' if settings.ORIENTATION_EMAILS_DEBUG else''}Vous avez un nouveau message 📩",
        orientation.prescriber.email,
        mjml2html(render_to_string("contact-prescriber.mjml", context)),
        from_email=(
            f"{orientation.service.structure.name} via DORA",
            settings.DEFAULT_FROM_EMAIL,
        ),
        tags=["orientation"],
        reply_to=[orientation.service.contact_email],
        cc=cc,
    )


def send_message_to_beneficiary(orientation, message, cc):
    context = {
        "data": orientation,
        "homepage_url": settings.FRONTEND_URL,
        "message": message,
        "support_email": settings.SUPPORT_EMAIL,
        "support_link": settings.ORIENTATION_SUPPORT_LINK,
    }

    send_mail(
        f"{'[Contact - Bénéficiaire] ' if settings.ORIENTATION_EMAILS_DEBUG else''}Vous avez un nouveau message 📩",
        orientation.beneficiary_email,
        mjml2html(render_to_string("contact-beneficiary.mjml", context)),
        from_email=(
            f"{orientation.service.structure.name} via DORA",
            settings.DEFAULT_FROM_EMAIL,
        ),
        tags=["orientation"],
        reply_to=[orientation.service.contact_email],
        cc=cc,
    )
