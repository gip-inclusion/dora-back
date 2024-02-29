import pytest
from django.core import mail

from dora.core.test_utils import make_structure, make_user
from dora.users.emails import (
    send_invitation_reminder,
    send_user_without_structure_notification,
)


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


@pytest.mark.parametrize(
    "deletion,subject",
    (
        (False, "Rappel : Identifiez votre structure sur DORA"),
        (True, "Dernier rappel avant suppression"),
    ),
)
def test_send_user_without_structure_notification(deletion, subject):
    user = make_user()

    send_user_without_structure_notification(user, deletion=deletion)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]
    assert mail.outbox[0].subject == subject
    assert user.last_name in mail.outbox[0].body
    assert "MailsTransactionnels" in mail.outbox[0].body
    assert "InscritSansStructure" in mail.outbox[0].body
    assert "Nous avons accès à vos données à caractère personnel" in mail.outbox[0].body
