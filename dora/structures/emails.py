from django.conf import settings
from django.template.loader import render_to_string
from django.utils.encoding import iri_to_uri
from furl import furl
from mjml import mjml2html

from dora.core.emails import send_mail


def send_invitation_email(member, host_fullname):
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
        "host_name": host_fullname,
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
