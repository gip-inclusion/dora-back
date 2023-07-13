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
        "[Envoyée - Structure porteuse] orientation Nouvelle demande d'orientation reçue",
        orientation.service.contact_email,
        mjml2html(render_to_string("orientation-created-structure.mjml", context)),
        from_email=(
            f"{orientation.prescriber.get_full_name()} via DORA",
            settings.DEFAULT_FROM_EMAIL,
        ),
        tags=["orientation"],
        reply_to=[orientation.referent_email, orientation.prescriber.email],
    )
    # Prescripteur
    send_mail(
        "[Envoyée - Prescripteur] Votre demande a bien été transmise !",
        orientation.prescriber.email,
        mjml2html(render_to_string("orientation-created-prescriber.mjml", context)),
        tags=["orientation"],
        reply_to=[orientation.service.contact_email, orientation.referent_email],
    )
    # Référent
    if (
        orientation.referent_email
        and orientation.referent_email != orientation.prescriber.email
    ):
        send_mail(
            "[Envoyée - Conseiller référent] Notification d'une demande d'orientation",
            orientation.referent_email,
            mjml2html(render_to_string("orientation-created-referent.mjml", context)),
            from_email=(
                f"{orientation.prescriber.get_full_name()} via DORA",
                settings.DEFAULT_FROM_EMAIL,
            ),
            tags=["orientation"],
            reply_to=[orientation.service.contact_email, orientation.prescriber.email],
        )
    # Bénéficiaire
    if orientation.beneficiary_email:
        send_mail(
            "[Envoyée - Bénéficiaire] Une orientation a été effectuée en votre nom",
            orientation.beneficiary_email,
            mjml2html(
                render_to_string("orientation-created-beneficiary.mjml", context)
            ),
            tags=["orientation"],
            reply_to=[orientation.referent_email, orientation.prescriber.email],
        )


def send_orientation_accepted_emails(
    orientation, prescriberMessage, beneficiaryMessage
):
    context = {
        "data": orientation,
        "homepage_url": settings.FRONTEND_URL,
        "support_email": settings.SUPPORT_EMAIL,
        "prescriberMessage": prescriberMessage,
        "beneficiaryMessage": beneficiaryMessage,
    }

    # Structure
    send_mail(
        "[Validée - Structure porteuse] Vous venez de valider une demande 🎉",
        [orientation.service.contact_email],
        mjml2html(render_to_string("orientation-accepted-structure.mjml", context)),
        tags=["orientation"],
    )

    # Prescripteur
    send_mail(
        "[Validée - Prescripteur] Votre demande a été acceptée ! 🎉",
        orientation.prescriber.email,
        mjml2html(render_to_string("orientation-accepted-prescriber.mjml", context)),
        from_email=(
            f"{orientation.structure.name} via DORA",
            settings.DEFAULT_FROM_EMAIL,
        ),
        tags=["orientation"],
        reply_to=[orientation.service.contact_email, orientation.referent_email],
    )
    # Référent
    if orientation.referent_email != orientation.prescriber.email:
        send_mail(
            "[Validée - Conseiller référent] Notification de l'acceptation d'une demande d'orientation",
            orientation.referent_email,
            mjml2html(render_to_string("orientation-accepted-referent.mjml", context)),
            from_email=(
                f"{orientation.structure.name} via DORA",
                settings.DEFAULT_FROM_EMAIL,
            ),
            tags=["orientation"],
            reply_to=[orientation.service.contact_email, orientation.prescriber.email],
        )
    # Bénéficiaire
    if orientation.beneficiary_email:
        send_mail(
            "[Validée - Bénéficiaire] Votre demande a été acceptée ! 🎉",
            orientation.beneficiary_email,
            mjml2html(
                render_to_string("orientation-accepted-beneficiary.mjml", context)
            ),
            from_email=(
                f"{orientation.structure.name} via DORA",
                settings.DEFAULT_FROM_EMAIL,
            ),
            tags=["orientation"],
            reply_to=[
                orientation.referent_email,
                orientation.prescriber.email,
                orientation.service.contact_email,
            ],
        )


def send_orientation_rejected_emails(orientation, message):
    context = {
        "data": orientation,
        "homepage_url": settings.FRONTEND_URL,
        "support_email": settings.SUPPORT_EMAIL,
        "message": message,
    }

    # Prescripteur
    send_mail(
        "[Refusée - Prescripteur] Votre demande a été refusée",
        [orientation.prescriber.email],
        mjml2html(render_to_string("orientation-rejected-prescriber.mjml", context)),
        from_email=(
            f"{orientation.service.structure.name} via DORA",
            settings.DEFAULT_FROM_EMAIL,
        ),
        tags=["orientation"],
        reply_to=[orientation.service.contact_email, orientation.referent_email],
    )

    # Referent
    send_mail(
        "[Refusée - Conseiller référent] Votre demande a été refusée",
        [orientation.referent_email],
        mjml2html(render_to_string("orientation-rejected-prescriber.mjml", context)),
        from_email=(
            f"{orientation.service.structure.name} via DORA",
            settings.DEFAULT_FROM_EMAIL,
        ),
        tags=["orientation"],
        reply_to=[orientation.service.contact_email, orientation.prescriber.email],
    )


def send_message_to_prescriber(orientation, message, cc_beneficiary, cc_referent):
    context = {
        "data": orientation,
        "homepage_url": settings.FRONTEND_URL,
        "message": message,
        "support_email": settings.SUPPORT_EMAIL,
    }

    recipients = [orientation.prescriber.email]
    if cc_referent and orientation.referent_email != orientation.prescriber.email:
        recipients.append(orientation.referent_email)
    if cc_beneficiary:
        recipients.append(orientation.beneficiary_email)
    send_mail(
        "[Contact - Prescripteur] Vous avez un nouveau message 📩",
        recipients,
        mjml2html(render_to_string("contact-prescriber.mjml", context)),
        from_email=(
            f"{orientation.service.structure.name} via DORA",
            settings.DEFAULT_FROM_EMAIL,
        ),
        tags=["orientation"],
        reply_to=[orientation.service.contact_email, orientation.referent_email],
    )


def send_message_to_beneficiary(orientation, message, cc_prescriber, cc_referent):
    context = {
        "data": orientation,
        "homepage_url": settings.FRONTEND_URL,
        "message": message,
        "support_email": settings.SUPPORT_EMAIL,
    }

    recipients = [orientation.beneficiary_email]
    if cc_prescriber:
        recipients.append(orientation.prescriber.email)
    if cc_referent and orientation.referent_email != orientation.prescriber.email:
        recipients.append(orientation.referent_email)

    send_mail(
        "[Contact - Bénéficiaire] Vous avez un nouveau message 📩",
        recipients,
        mjml2html(render_to_string("contact-beneficiary.mjml", context)),
        from_email=(
            f"{orientation.service.structure.name} via DORA",
            settings.DEFAULT_FROM_EMAIL,
        ),
        tags=["orientation"],
        reply_to=[
            orientation.service.contact_email,
            orientation.referent_email,
            orientation.prescriber.email,
        ],
    )
