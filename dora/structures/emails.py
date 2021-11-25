from django.conf import settings
from django.template.loader import render_to_string

from dora.core.emails import send_mail


def send_invitation_email(member, admin_user_fullname, token):
    params = {
        "recipient_email": member.user.email,
        "recipient_name": member.user.get_short_name(),
        "admin_name": admin_user_fullname,
        "structure_name": member.structure.name,
        "cta_link": f"{settings.FRONTEND_URL}/auth/accepter-invitation?token={token}&membership={member.id}",
        "homepage_url": settings.FRONTEND_URL,
    }
    txt_msg = render_to_string("invitation.txt", params)
    html_msg = render_to_string("invitation.html", params)

    send_mail(
        "[DORA] Votre invitation sur DORA",
        member.user.email,
        txt_msg,
        html_content=html_msg,
        tags=["invitation"],
    )


def send_invitation_accepted_notification(member, admin_user):
    params = {
        "recipient_email": admin_user.email,
        "recipient_name": admin_user.get_short_name(),
        "new_member_full_name": member.user.get_full_name(),
        "new_member_email": member.user.email,
        "structure_name": member.structure.name,
        "homepage_url": settings.FRONTEND_URL,
    }

    txt_msg = render_to_string("notification-invitation-accepted.txt", params)
    html_msg = render_to_string("notification-invitation-accepted.html", params)

    send_mail(
        "[DORA] Invitation acceptée",
        admin_user.email,
        txt_msg,
        html_content=html_msg,
        tags=["invitation-accepted"],
    )
