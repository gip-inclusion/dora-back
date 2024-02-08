import pytest
from dateutil.relativedelta import relativedelta
from django.core import mail
from django.utils import timezone
from freezegun import freeze_time

from dora.core.test_utils import make_user
from dora.notifications.models import Notification
from dora.users.models import User

from ..core import Task
from ..users import UserAccountDeletionTask


@pytest.fixture
def user_account_deletion_task():
    return UserAccountDeletionTask()


def test_user_account_deletion_registered():
    assert UserAccountDeletionTask in Task.registered_tasks()


def test_user_account_deletation_should_trigger(user_account_deletion_task):
    user = make_user(last_login=timezone.now())

    assert user not in user_account_deletion_task.candidates()

    ok, _, _ = user_account_deletion_task.run()

    assert not ok

    old_user = make_user(last_login=timezone.now() - relativedelta(years=2))

    assert old_user in user_account_deletion_task.candidates()

    ok, _, _ = user_account_deletion_task.run()

    assert ok

    n = Notification.objects.pending().first()

    assert n
    assert n.counter == 1

    with freeze_time(timezone.now() + relativedelta(days=29)):
        ok, _, _ = user_account_deletion_task.run()

        assert not ok

        n.refresh_from_db()

        assert n.counter == 1

        # toujours là, mais plus pour longtemps ...
        old_user.refresh_from_db()

        assert old_user

    with freeze_time(timezone.now() + relativedelta(days=30)):
        ok, _, _ = user_account_deletion_task.run()
        assert ok
    with pytest.raises(User.DoesNotExist):
        # à ce point, le compte utilisateur a été supprimé
        old_user.refresh_from_db()

    with pytest.raises(Notification.DoesNotExist):
        # et la notification aussi
        n.refresh_from_db()


def test_process_user_account_deletion(user_account_deletion_task):
    old_user = make_user(last_login=timezone.now() - relativedelta(years=2))

    ok, _, _ = user_account_deletion_task.run()

    assert ok
    assert 1 == len(mail.outbox)
    assert [old_user.email] == mail.outbox[0].to
