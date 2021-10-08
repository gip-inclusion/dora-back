from django.conf import settings
from django.template.loader import render_to_string

from dora.core.emails import send_mail


def send_invitation_email(member, admin_user, token):
    params = {
        "recipient_email": member.user.email,
        "recipient_name": member.user.name,
        "admin_name": admin_user.name or admin_user.email,
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
