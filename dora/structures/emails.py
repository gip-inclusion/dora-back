from django.conf import settings
from django.template.loader import render_to_string
from django.utils.encoding import iri_to_uri
from furl import furl
from mjml import mjml2html

from dora.core.emails import send_mail


def send_invitation_email(member, inviter_name):
    structure = member.structure
    invitation_link = furl(settings.FRONTEND_URL).add(
        path="/auth/invitation",
        args={
            "login_hint": iri_to_uri(member.user.email),
            "structure": structure.slug,
        },
    )
    params = {
        "recipient_email": member.user.email,
        "recipient_name": member.user.get_short_name(),
        "inviter_name": inviter_name,
        "structure": structure,
        "cta_link": invitation_link,
        "with_legal_info": True,
        "with_dora_info": True,
    }
    body = mjml2html(render_to_string("invitation.mjml", params))

    send_mail(
        "[DORA] Votre invitation sur DORA",
        member.user.email,
        body,
        tags=["invitation"],
    )


def send_invitation_accepted_notification(member, admin_user):
    params = {
        "recipient_email": admin_user.email,
        "recipient_name": admin_user.get_short_name(),
        "new_member_full_name": member.user.get_full_name(),
        "new_member_email": member.user.email,
        "structure_name": member.structure.name,
    }

    body = render_to_string("notification-invitation-accepted.html", params)

    send_mail(
        "[DORA] Invitation acceptée",
        admin_user.email,
        body,
        tags=["invitation-accepted"],
    )


def send_access_requested_notification(member, admin_user):
    params = {
        "recipient_email": admin_user.email,
        "recipient_name": admin_user.get_short_name(),
        "new_member_full_name": member.user.get_full_name(),
        "new_member_email": member.user.email,
        "structure_name": member.structure.name,
        "cta_link": f"{settings.FRONTEND_URL}/structures/{member.structure.slug}",
    }

    body = render_to_string("notification-access-request.html", params)

    send_mail(
        "[DORA] Demande d’accès à votre structure",
        admin_user.email,
        body,
        tags=["access-request"],
    )


def send_access_granted_notification(member):
    params = {
        "structure_name": member.structure.name,
        "cta_link": f"{settings.FRONTEND_URL}/structures/{member.structure.slug}",
    }

    body = render_to_string("notification-access-granted.html", params)

    send_mail(
        "[DORA] Accès accordé",
        member.user.email,
        body,
        tags=["access-granted"],
    )


def send_access_rejected_notification(member):
    params = {
        "structure_name": member.structure.name,
    }

    body = render_to_string("notification-access-rejected.html", params)

    send_mail(
        "[DORA] Accès refusé",
        member.user.email,
        body,
        tags=["access-rejected"],
    )


def send_branch_created_notification(structure, branch, admin_user):
    params = {
        "recipient_email": admin_user.email,
        "recipient_name": admin_user.get_short_name(),
        "structure_name": structure.name,
        "cta_link": f"{settings.FRONTEND_URL}/structures/{branch.slug}",
        "branch_name": branch.name,
    }

    body = render_to_string("notification-branch-created.html", params)

    send_mail(
        "[DORA] Votre antenne a été créée",
        admin_user.email,
        body,
        tags=["branch-created"],
    )


def send_orphan_structure_notification(structure):
    # notification aux structures "orphelines" (pas de membre actif)
    cta_link = furl(settings.FRONTEND_URL) / "auth" / "invitation"
    cta_link.add(
        {
            "structure": structure.slug,
            "mtm_campaign": "MailsTransactionnels",
            "mtm_kwd": "InvitationStructuresOrphelines",
        }
    )
    context = {
        "structure": structure,
        "dora_doc_link": "https://aide.dora.inclusion.beta.gouv.fr/fr/article/decouvrir-et-faire-decouvrir-dora-1nyj6f1/",
        "webinar_link": "https://app.livestorm.co/dora-1/presentation-dora",
        "cta_link": cta_link.url,
    }

    send_mail(
        f"Votre structure n’a pas encore de membre actif sur DORA ({
            structure.name})",
        structure.email,
        mjml2html(render_to_string("notification-orphan-structure.mjml", context)),
        tags=["orphan-structure"],
    )


def send_structure_activation_notification(structure):
    # notification envoyée aux administrateurs de structure
    # pour une première activation de service
    cta_link = furl(settings.FRONTEND_URL) / "structures" / structure.slug / "services"
    cta_link.add(
        {
            "mtm_campaign": "MailsTransactionnels",
            "mtm_kwd": "RelanceActivationService",
        }
    )
    context = {
        "structure": structure,
        "dora_doc_link": "https://aide.dora.inclusion.beta.gouv.fr/fr/article/referencer-son-offre-de-service-xpivaw/",
        "webinar_link": "https://app.livestorm.co/dora-1/presentation-dora",
        "cta_link": cta_link.url,
    }
    for pm in structure.putative_membership.filter(is_admin=True).select_related(
        "user"
    ):
        send_mail(
            f"Votre structure n’a pas encore publié de service sur DORA ({ structure.name})",
            pm.user.email,
            mjml2html(
                render_to_string("notification-service-activation.mjml", context),
            ),
            tags=["structure-service-activation"],
        )
