from django.conf import settings
from django.core.files.storage import default_storage
from django.template.loader import render_to_string
from django.utils import timezone
from mjml import mjml2html

from dora.core.emails import send_mail
from dora.orientations.models import ContactPreference

debug = settings.ORIENTATION_EMAILS_DEBUG


def beneficiaries_has_alternate_contact_methods(orientation):
    beneficiaries_contact_methods = [
        method
        for method in [
            orientation.beneficiary_phone,
            orientation.beneficiary_email,
            orientation.beneficiary_other_contact_method,
        ]
        if method
    ]

    return len(beneficiaries_contact_methods) > len(
        orientation.beneficiary_contact_preferences
    )


def send_orientation_created_emails(orientation):
    context = {
        "data": orientation,
        "ContactPreference": ContactPreference,
        "support_email": settings.SUPPORT_EMAIL,
        "orientation_support_link": settings.ORIENTATION_SUPPORT_LINK,
        "beneficiaries_has_alternate_contact_methods": beneficiaries_has_alternate_contact_methods(
            orientation
        ),
        "attachments": [
            {"name": a, "url": default_storage.url(a)}
            for a in orientation.beneficiary_attachments
        ],
    }
    # Structure porteuse
    send_mail(
        f"{'[Envoyée - Structure porteuse] ' if debug else ''}Nouvelle demande d’orientation reçue",
        orientation.get_contact_email(),
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
        f"{'[Envoyée - Prescripteur] ' if debug else ''}Votre demande a bien été transmise !",
        orientation.prescriber.email,
        mjml2html(render_to_string("orientation-created-prescriber.mjml", context)),
        tags=["orientation"],
        reply_to=[orientation.get_contact_email()],
    )
    # Référent
    if (
        orientation.referent_email
        and orientation.referent_email != orientation.prescriber.email
    ):
        send_mail(
            f"{'[Envoyée - Conseiller référent] ' if debug else ''}Notification d’une demande d’orientation",
            orientation.referent_email,
            mjml2html(render_to_string("orientation-created-referent.mjml", context)),
            tags=["orientation"],
            reply_to=[orientation.prescriber.email],
        )
    # Bénéficiaire
    if orientation.beneficiary_email:
        send_mail(
            f"{'[Envoyée - Bénéficiaire] ' if debug else ''}Une orientation a été effectuée en votre nom",
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
        "support_email": settings.SUPPORT_EMAIL,
        "orientation_support_link": settings.ORIENTATION_SUPPORT_LINK,
        "prescriber_message": prescriber_message,
        "beneficiary_message": beneficiary_message,
    }

    # Structure
    send_mail(
        f"{'[Validée - Structure porteuse] ' if debug else ''}Vous venez de valider une demande 🎉",
        [orientation.get_contact_email()],
        mjml2html(render_to_string("orientation-accepted-structure.mjml", context)),
        tags=["orientation"],
    )

    # Prescripteur
    send_mail(
        f"{'[Validée - Prescripteur] ' if debug else ''}Votre demande a été acceptée ! 🎉",
        orientation.prescriber.email,
        mjml2html(render_to_string("orientation-accepted-prescriber.mjml", context)),
        from_email=(
            f"{orientation.get_structure_name()} via DORA",
            settings.DEFAULT_FROM_EMAIL,
        ),
        tags=["orientation"],
        reply_to=[orientation.get_contact_email()],
    )
    # Référent
    if (
        orientation.referent_email
        and orientation.referent_email != orientation.prescriber.email
    ):
        send_mail(
            f"{'[Validée - Conseiller référent] ' if debug else ''}Notification de l’acceptation d’une demande d’orientation",
            orientation.referent_email,
            mjml2html(render_to_string("orientation-accepted-referent.mjml", context)),
            from_email=(
                f"{orientation.get_structure_name()} via DORA",
                settings.DEFAULT_FROM_EMAIL,
            ),
            tags=["orientation"],
            reply_to=[orientation.prescriber.email],
        )
    # Bénéficiaire
    if orientation.beneficiary_email:
        send_mail(
            f"{'[Validée - Bénéficiaire] ' if debug else ''}Votre demande a été acceptée ! 🎉",
            orientation.beneficiary_email,
            mjml2html(
                render_to_string("orientation-accepted-beneficiary.mjml", context)
            ),
            from_email=(
                f"{orientation.get_structure_name()} via DORA",
                settings.DEFAULT_FROM_EMAIL,
            ),
            tags=["orientation"],
            reply_to=[orientation.get_contact_email()],
        )


def send_orientation_rejected_emails(orientation, message):
    context = {
        "data": orientation,
        "support_email": settings.SUPPORT_EMAIL,
        "orientation_support_link": settings.ORIENTATION_SUPPORT_LINK,
        "message": message,
    }

    # Structure
    send_mail(
        f"{'[Refusée - Structure porteuse] ' if debug else ''}Vous venez de refuser une demande",
        [orientation.get_contact_email()],
        mjml2html(render_to_string("orientation-rejected-structure.mjml", context)),
        tags=["orientation"],
    )

    # Prescripteur
    send_mail(
        f"{'[Refusée - Prescripteur] ' if debug else ''}Votre demande d’orientation a été refusée",
        [orientation.prescriber.email],
        mjml2html(render_to_string("orientation-rejected-prescriber.mjml", context)),
        from_email=(
            f"{orientation.get_structure_name()} via DORA",
            settings.DEFAULT_FROM_EMAIL,
        ),
        tags=["orientation"],
        reply_to=[orientation.get_contact_email()],
    )

    if (
        orientation.referent_email
        and orientation.referent_email != orientation.prescriber.email
    ):
        # Referent
        send_mail(
            f"{'[Refusée - Conseiller référent] ' if debug else ''}Votre demande d’orientation a été refusée",
            [orientation.referent_email],
            mjml2html(
                render_to_string("orientation-rejected-prescriber.mjml", context)
            ),
            from_email=(
                f"{orientation.get_structure_name()} via DORA",
                settings.DEFAULT_FROM_EMAIL,
            ),
            tags=["orientation"],
            reply_to=[orientation.get_contact_email()],
        )


def send_message_to_prescriber(orientation, message, cc):
    context = {
        "data": orientation,
        "message": message,
        "support_email": settings.SUPPORT_EMAIL,
        "orientation_support_link": settings.ORIENTATION_SUPPORT_LINK,
    }
    send_mail(
        f"{'[Contact - Prescripteur] ' if debug else ''}Vous avez un nouveau message 📩",
        orientation.prescriber.email,
        mjml2html(render_to_string("contact-prescriber.mjml", context)),
        from_email=(
            f"{orientation.get_structure_name()} via DORA",
            settings.DEFAULT_FROM_EMAIL,
        ),
        tags=["orientation"],
        reply_to=[orientation.get_contact_email()],
        cc=cc,
    )


def send_message_to_beneficiary(orientation, message, cc):
    context = {
        "data": orientation,
        "message": message,
        "support_email": settings.SUPPORT_EMAIL,
        "orientation_support_link": settings.ORIENTATION_SUPPORT_LINK,
    }

    send_mail(
        f"{'[Contact - Bénéficiaire] ' if debug else ''}Vous avez un nouveau message 📩",
        orientation.beneficiary_email,
        mjml2html(render_to_string("contact-beneficiary.mjml", context)),
        from_email=(
            f"{orientation.get_structure_name()} via DORA",
            settings.DEFAULT_FROM_EMAIL,
        ),
        tags=["orientation"],
        reply_to=[orientation.get_contact_email()],
        cc=cc,
    )


def send_orientation_reminder_emails(orientation):
    context = {
        "data": orientation,
        "support_email": settings.SUPPORT_EMAIL,
        "orientation_support_link": settings.ORIENTATION_SUPPORT_LINK,
        "elapsed_days": (timezone.now() - orientation.creation_date).days,
        "ContactPreference": ContactPreference,
        "beneficiaries_has_alternate_contact_methods": beneficiaries_has_alternate_contact_methods(
            orientation
        ),
        "attachments": [
            {"name": a, "url": default_storage.url(a)}
            for a in orientation.beneficiary_attachments
        ],
    }

    send_mail(
        f"{'[Notification - Structure] ' if debug else ''}Relance – Demande d’orientation en attente",
        orientation.get_contact_email(),
        mjml2html(render_to_string("notification-structure.mjml", context)),
        tags=["orientation"],
    )
    cc = []
    if (
        orientation.referent_email
        and orientation.referent_email != orientation.prescriber.email
    ):
        cc.append(orientation.referent_email)

    send_mail(
        f"{'[Notification - Prescripteur] ' if debug else ''}Relance envoyée – Demande d’orientation en attente",
        orientation.prescriber.email,
        mjml2html(render_to_string("notification-prescriber.mjml", context)),
        tags=["orientation"],
        cc=cc,
    )
