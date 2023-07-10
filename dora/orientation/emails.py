from django.conf import settings
from django.template.loader import render_to_string
from mjml import mjml2html

from dora.core.emails import send_mail


def send_orientation_created_emails(orientation):
    context = {
        "data": orientation,
        "homepage_url": settings.FRONTEND_URL,
        "magic_link": orientation.get_magic_link(),
    }
    # Structure porteuse
    send_mail(
        "[DORA] Nouvelle demande d'orientation reçue",
        orientation.service.contact_email,
        mjml2html(render_to_string("orientation-created-structure.mjml", context)),
        from_email=(
            f"{orientation.prescriber.get_full_name()} via DORA",
            settings.DEFAULT_FROM_EMAIL,
        ),
        tags=["orientation"],
        reply_to=[orientation.referent_email, orientation.prescriber.email],
        attachments=orientation.beneficiary_attachments,
    )
    # Prescripteur
    send_mail(
        "[DORA] Votre demande a bien été transmise !",
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
            "[DORA] Notification d'une demande d'orientation",
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
            "[DORA] Une orientation a été effectuée en votre nom",
            orientation.beneficiary_email,
            mjml2html(
                render_to_string("orientation-created-beneficiary.mjml", context)
            ),
            tags=["orientation"],
            reply_to=[orientation.referent_email, orientation.prescriber.email],
        )


# def send_orientation_accepted_emails(orientation):
#     context = {
#         "data": orientation,
#         "homepage_url": settings.FRONTEND_URL,
#         "magic_link": orientation.get_magic_link(),
#     }
#
#     # Prescripteur
#     send_mail(
#         "[DORA] Votre demande a bien été transmise !",
#         orientation.prescriber.email,
#         mjml2html(render_to_string("orientation-accepted-prescriber.mjml", context)),
#         tags=["orientation"],
#         reply_to=[orientation.service.contact_email, orientation.referent_email],
#     )
#     # Référent
#     if (
#         orientation.referent_email
#         and orientation.referent_email != orientation.prescriber.email
#     ):
#         send_mail(
#             "[DORA] Notification d'une demande d'orientation",
#             orientation.referent_email,
#             mjml2html(render_to_string("orientation-accepted-referent.mjml", context)),
#             from_email=(
#                 f"{orientation.prescriber.get_full_name()} via DORA",
#                 settings.DEFAULT_FROM_EMAIL,
#             ),
#             tags=["orientation"],
#             reply_to=[orientation.service.contact_email, orientation.prescriber.email],
#         )
#     # Bénéficiaire
#     if orientation.beneficiary_email:
#         send_mail(
#             "[DORA] Une orientation a été effectuée en votre nom",
#             orientation.beneficiary_email,
#             mjml2html(
#                 render_to_string("orientation-accepted-beneficiary.mjml", context)
#             ),
#             tags=["orientation"],
#             reply_to=[orientation.referent_email, orientation.prescriber.email],
#         )
