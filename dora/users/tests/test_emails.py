from django.core import mail

from dora.core.test_utils import make_structure, make_user
from dora.users.emails import send_invitation_reminder


def test_send_invitation_reminder():
    user = make_user()
    structure = make_structure(putative_member=user)

    send_invitation_reminder(user, structure)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]
    assert (
        mail.outbox[0].subject
        == f"Rappel : Acceptez l'invitation à rejoindre {structure.name} sur DORA"
    )
    assert structure.name in mail.outbox[0].body
    assert "/auth/invitation" in mail.outbox[0].body
