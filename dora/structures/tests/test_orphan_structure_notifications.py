from io import StringIO

from django.core import mail
from django.core.management import call_command
from model_bakery import baker

from dora.core.test_utils import make_structure


def run_management_command(wet_run=False) -> StringIO:
    output = StringIO()
    call_command("send_orphan_structures_notifications", wet_run=wet_run, stdout=output)
    return output


def test_wet_run():
    assert "DRY-RUN" in run_management_command().getvalue()
    assert "PRODUCTION RUN" in run_management_command(wet_run=True).getvalue()


def test_notify_orphan_structure():
    structure = make_structure(email="woody@pixar.com")
    run_management_command(wet_run=True)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [structure.email]
    assert (
        mail.outbox[0].subject
        == f"Votre structure n’a pas encore de membre actif sur DORA ({structure.name})"
    )
    assert structure.name in mail.outbox[0].body
    assert f"/structures/{structure.slug}" in mail.outbox[0].body


def test_do_not_notify_structures_with_members():
    make_structure(
        user=baker.make("users.user", is_valid=True), email="buzz@lightyear.com"
    )
    run_management_command(wet_run=True)

    assert len(mail.outbox) == 0


def test_do_not_notify_structures_with_putative_memberships():
    make_structure(
        putative_member=baker.make("users.user", is_valid=True),
        email="buzz@lightyear.com",
    )
    run_management_command(wet_run=True)

    assert len(mail.outbox) == 0


def test_do_not_try_to_notify_orphan_structure_without_email():
    make_structure(user=baker.make("users.user", is_valid=True), email="")
    run_management_command(wet_run=True)

    assert len(mail.outbox) == 0
