from dateutil.relativedelta import relativedelta
from django.core import mail
from django.templatetags.l10n import localize
from django.utils import timezone

from dora.core.test_utils import make_structure, make_user
from dora.users.emails import (
    send_account_deletion_notification,
    send_invitation_reminder,
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


def test_send_account_deletion_notification():
    user = make_user(email="buzz@lightyear.com")

    send_account_deletion_notification(user)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]
    assert mail.outbox[0].subject == "DORA - Suppression prochaine de votre compte"
    assert (
        localize(timezone.localdate() + relativedelta(days=30)) in mail.outbox[0].body
    )
    assert "/auth/connexion" in mail.outbox[0].body
    assert "MailsTransactionnels" in mail.outbox[0].body
    assert "RelanceInactif" in mail.outbox[0].body
