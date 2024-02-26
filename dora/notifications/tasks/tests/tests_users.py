import uuid

import pytest
from dateutil.relativedelta import relativedelta
from django.core import mail
from django.utils import timezone
from freezegun import freeze_time

from dora.core.test_utils import make_structure, make_user
from dora.notifications.models import Notification
from dora.users.models import User

from ..core import Task
from ..users import UsersWithoutStructureTask


@pytest.fixture
def user_without_structure_task():
    return UsersWithoutStructureTask()


def test_user_without_structure_task_is_registered():
    assert UsersWithoutStructureTask in Task.registered_tasks()


def test_user_without_structure_task_candidates(user_without_structure_task):
    # pas d'id IC
    nok_user = make_user()
    assert nok_user not in user_without_structure_task.candidates()

    # adresse e-mail non validée
    nok_user = make_user(is_valid=False)
    assert nok_user not in user_without_structure_task.candidates()

    # utilisateurs incrits depuis plus de 4 mois exclus
    nok_user = make_user(
        ic_id=uuid.uuid4(), date_joined=timezone.now() - relativedelta(months=4, days=1)
    )
    assert nok_user not in user_without_structure_task.candidates()

    # membres de structure exclus
    nok_user = make_user(structure=make_structure(), ic_id=uuid.uuid4())
    assert nok_user not in user_without_structure_task.candidates()

    # utilisateurs invités exclus
    nok_user = make_user(ic_id=uuid.uuid4())
    make_structure(putative_member=nok_user)
    assert nok_user not in user_without_structure_task.candidates()

    # candidat potentiel
    ok_user = make_user(ic_id=uuid.uuid4())
    assert ok_user in user_without_structure_task.candidates()


def test_user_without_structure_task_should_trigger(user_without_structure_task):
    user = make_user(ic_id=uuid.uuid4())

    # première notification à +1j
    ok, _, _ = user_without_structure_task.run()
    assert not ok

    notification = Notification.objects.first()
    assert notification.is_pending

    now = timezone.now()

    for cnt, day in enumerate((1, 5, 10, 15), 1):
        with freeze_time(now + relativedelta(days=day)):
            ok, _, _ = user_without_structure_task.run()
            assert ok

            notification.refresh_from_db()
            assert notification.counter == cnt
            assert notification.is_pending

            # on vérifie qu'un e-mail est bien envoyé
            # testé plus en détails dans la partie e-mail
            assert len(mail.outbox) == cnt
            assert mail.outbox[cnt - 1].to == [user.email]

        with freeze_time(now + relativedelta(days=day + 1)):
            ok, _, _ = user_without_structure_task.run()
            assert not ok

            notification.refresh_from_db()
            assert notification.counter == cnt
            assert notification.is_pending

    notification.refresh_from_db()
    assert notification.counter == 4
    assert notification.is_pending

    # on teste la dernière iteration de la notification (+4 mois)
    with freeze_time(now + relativedelta(months=4)):
        ok, _, _ = user_without_structure_task.run()
        assert ok

        # la notification ne doit plus exister (l'utilisateur propriétaire a été supprimé)
        with pytest.raises(Notification.DoesNotExist):
            notification.refresh_from_db()

    # le compte utilisateur doit avoir été supprimé
    with pytest.raises(User.DoesNotExist):
        user.refresh_from_db()
