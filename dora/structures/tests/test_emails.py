from django.core import mail

from dora.core.test_utils import make_structure

from ..emails import send_orphan_structure_notification


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
    assert f"/structures/{structure.slug}" in mail.outbox[0].body
    assert "mtm_campaign=MailsTransactionnels" in mail.outbox[0].body
    assert "mtm_kwd=InvitationStructuresOrphelines" in mail.outbox[0].body
