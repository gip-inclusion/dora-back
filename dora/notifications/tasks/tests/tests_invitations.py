from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone
from freezegun import freeze_time
from model_bakery import baker

from dora.core.test_utils import make_structure, make_user
from dora.notifications.models import Notification
from dora.users.models import User

from ..core import Task
from ..invitations import InvitedUsersTask


@pytest.fixture
def invited_users_task():
    return InvitedUsersTask()


def test_invited_users_task_registered():
    assert InvitedUsersTask in Task.registered_tasks()


def test_invited_user_task_should_not_trigger(invited_users_task):
    make_structure(user=make_user())

    # pas d'invitations en attente
    ok, _, _ = invited_users_task.run()
    assert not ok

    # les notifications ne se déclenchent qu'après un jour
    make_structure(putative_member=make_user())
    ok, _, _ = invited_users_task.run()
    assert not ok


def test_invited_user_task_should_trigger(invited_users_task):
    structure = make_structure()
    user = make_user()
    admin = make_user(structure=structure, is_admin=True)

    # les invitations doivent avoir été envoyées par un admin (CAT 1)
    structure.putative_membership.add(
        baker.make(
            "StructurePutativeMember",
            user=user,
            invited_by_admin=True,
            structure=structure,
        )
    )

    ok, _, _ = invited_users_task.run()

    assert 1 == len(invited_users_task.candidates())

    # pas encore déclenchée ...
    assert not ok
    # mais une notification a bien été créée
    assert 1 == Notification.objects.count()

    notification = Notification.objects.first()

    # premiere phase : envois de notifications à l'utilisateur
    for idx, day in enumerate([1, 5, 10, 15]):
        with freeze_time(timezone.now() + timedelta(days=day)):
            ok, _, _ = invited_users_task.run()
            assert ok

            notification.refresh_from_db()
            assert idx + 1 == notification.counter

        # la notification ne doit pas se déclencher dans l'intervalle ...
        with freeze_time(timezone.now() + timedelta(days=day + 1)):
            ok, _, _ = invited_users_task.run()
            assert not ok

            notification.refresh_from_db()
            assert idx + 1 == notification.counter

    # on vérifie sommairement les e-mails envoyés
    # (le test du contenu est fait dans l'app `structures`)
    assert len(mail.outbox) == 4
    for msg in mail.outbox:
        assert msg.to == [user.email]
    assert notification.is_pending

    offset = notification.counter + 1

    # deuxième phase : envoi des notifications aux admins
    for idx, day in enumerate([20, 90]):
        with freeze_time(timezone.now() + timedelta(days=day)):
            ok, _, _ = invited_users_task.run()
            assert ok

            notification.refresh_from_db()
            # les notifications aux admins commencent à la 5e occurence
            assert idx + offset == notification.counter

        # la notification ne doit pas se déclencher dans l'intervalle ...
        with freeze_time(timezone.now() + timedelta(days=day + 1)):
            ok, _, _ = invited_users_task.run()
            assert not ok

            notification.refresh_from_db()
            assert idx + offset == notification.counter

    assert len(mail.outbox) == 6
    assert mail.outbox[4].to == [admin.email]
    assert mail.outbox[5].to == [admin.email]
    assert notification.is_pending

    # troisìème phase : suppression de l'invitation et de l'utilisateur
    with freeze_time(timezone.now() + timedelta(days=120)):
        ok, _, _ = invited_users_task.run()
        assert ok

        ok, _, _ = invited_users_task.run()
        assert not ok

    assert structure.putative_membership.count() == 0

    # à ce point, la notification, n'ayant plus de propriétaire, doit avoir été détruite
    with pytest.raises(Notification.DoesNotExist):
        notification.refresh_from_db()

    # le membre invité également
    with pytest.raises(User.DoesNotExist):
        user.refresh_from_db()
