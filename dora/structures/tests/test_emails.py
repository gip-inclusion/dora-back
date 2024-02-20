from django.core import mail

from dora.core.test_utils import make_structure, make_user

from ..emails import (
    send_admin_invited_users_20_notification,
    send_admin_invited_users_90_notification,
    send_admin_self_invited_users_notification,
    send_orphan_structure_notification,
    send_structure_activation_notification,
)


def test_send_orphan_structure_notification():
    structure = make_structure(email="woody@pixar.com")

    send_orphan_structure_notification(structure)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [structure.email]
    assert (
        mail.outbox[0].subject
        == f"Votre structure n’a pas encore de membre actif sur DORA ({structure.name})"
    )
    assert structure.name in mail.outbox[0].body
    assert f"/auth/invitation?structure={structure.slug}" in mail.outbox[0].body
    assert "mtm_campaign=MailsTransactionnels" in mail.outbox[0].body
    assert "mtm_kwd=InvitationStructuresOrphelines" in mail.outbox[0].body
    assert "https://aide.dora.inclusion.beta.gouv.fr" in mail.outbox[0].body
    assert "https://app.livestorm.co/dora-1/presentation-dora" in mail.outbox[0].body


def test_send_first_admin_notification_for_pending_invitation():
    putative_member = make_user()
    structure = make_structure(putative_member=putative_member)
    admin_user = make_user(structure=structure, is_admin=True)

    send_admin_invited_users_20_notification(structure, putative_member)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [admin_user.email]
    assert mail.outbox[0].subject == "Invitation non acceptée : Action requise"
    assert structure.name in mail.outbox[0].body
    assert putative_member.email in mail.outbox[0].body
    assert "https://aide.dora.inclusion.beta.gouv.fr/" in mail.outbox[0].body
    assert (
        "gerer-le-compte-de-ses-collaborateurs-en-tant-quadministrateur-xkonvm"
        in mail.outbox[0].body
    )


def test_send_second_admin_notification_for_pending_invitation():
    putative_member = make_user()
    structure = make_structure(putative_member=putative_member)
    admin_user = make_user(structure=structure, is_admin=True)

    send_admin_invited_users_90_notification(structure, putative_member)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [admin_user.email]
    assert (
        mail.outbox[0].subject
        == "Action requise : une de vos invitations sera bientôt désactivée"
    )
    assert structure.name in mail.outbox[0].body
    assert putative_member.email in mail.outbox[0].body


def test_send_admin_self_invited_users_notification():
    putative_member = make_user()
    structure = make_structure(putative_member=putative_member)
    admin_user = make_user(structure=structure, is_admin=True)

    send_admin_self_invited_users_notification(structure, putative_member)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [admin_user.email]
    assert mail.outbox[0].subject == "Rappel : Demande de rattachement en attente"
    assert structure.name in mail.outbox[0].body
    assert putative_member.email in mail.outbox[0].body
    assert putative_member.first_name in mail.outbox[0].body
    assert putative_member.last_name in mail.outbox[0].body
    assert f"structures/{structure.slug}/collaborateurs" in mail.outbox[0].body
    assert "https://aide.dora.inclusion.beta.gouv.fr/" in mail.outbox[0].body
    assert (
        "gerer-le-compte-de-ses-collaborateurs-en-tant-quadministrateur-xkonvm"
        in mail.outbox[0].body
    )

def test_send_structure_activation_notification():
    admin = make_user(email="jessie@pixar.com")
    structure = make_structure(putative_member=admin)
    invitation = structure.putative_membership.first()
    invitation.is_admin = True
    invitation.save()

    send_structure_activation_notification(structure)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [admin.email]
    assert (
        mail.outbox[0].subject
        == f"Votre structure n’a pas encore publié de service sur DORA ({structure.name})"
    )
    assert structure.name in mail.outbox[0].body
    assert f"/structures/{structure.slug}/services" in mail.outbox[0].body
    assert "mtm_campaign=MailsTransactionnels" in mail.outbox[0].body
    assert "mtm_kwd=RelanceActivationService" in mail.outbox[0].body
    assert "https://aide.dora.inclusion.beta.gouv.fr" in mail.outbox[0].body
    assert "https://app.livestorm.co/dora-1/presentation-dora" in mail.outbox[0].body
