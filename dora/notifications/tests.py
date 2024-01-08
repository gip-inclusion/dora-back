import pytest
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.utils import timezone

from dora.core.test_utils import make_structure

from .enums import NotificationStatus, TaskType
from .models import Notification, NotificationError

# note : le premier type de propriétaire implémenté est la structure
# les tests du modèle se basent sur des notification ayant ce type de propriétaire


@pytest.fixture()
def notification():
    return Notification(
        owner_structure=make_structure(), task_type=TaskType.ORPHAN_STRUCTURES
    )


@pytest.mark.parametrize("status", NotificationStatus.values)
def test_notification_queryset_status(notification, status):
    notification.status = status
    notification.save()

    # ces méthodes du queryset reprennent le nom du status
    qs_method = getattr(Notification.objects, status)

    assert len(qs_method()) == 1


@pytest.mark.parametrize("status", NotificationStatus.values)
def test_notification_str(notification, status):
    notification.status = status
    assert str(notification.pk) in str(notification)
    assert notification.status in str(notification)
    assert notification.task_type in str(notification)


def test_constraints(notification):
    notification.owner_structure = None

    with pytest.raises(IntegrityError, match="check_structure"):
        notification.save()
    ...


def test_unicity(notification):
    notification.save()

    # même type de tâche pour une structure donnée
    n = Notification(
        task_type=notification.task_type, owner_structure=notification.owner_structure
    )
    with pytest.raises(IntegrityError, match="duplicate key value"):
        n.save()
    ...


def test_owner(notification):
    assert notification.owner == notification.owner_structure
    with pytest.raises(NotificationError):
        notification.owner_structure = None
        notification.owner
    ...


def test_expired(notification):
    assert not notification.expired

    notification.expires_at = timezone.now()

    assert notification.expired


def test_trigger(notification):
    notification.trigger()
    notification.refresh_from_db()

    assert notification.counter == 1
    assert notification.updated_at < timezone.now()


def test_complete(notification):
    notification.complete()
    notification.refresh_from_db()

    assert notification.counter == 0
    assert notification.updated_at < timezone.now()

    notification.counter = 1
    notification.complete()
    notification.refresh_from_db()

    # ne doit pas changer
    assert notification.counter == 0

    notification.expired_at = timezone.now()
    notification.status = NotificationStatus.EXPIRED
    notification.save()

    notification.complete()
    notification.refresh_from_db()

    # ne doit pas changer
    assert notification.counter == 0
    assert notification.status == NotificationStatus.EXPIRED


def test_clean(notification):
    # doit passer sans Exception
    notification.clean()

    # type inconnu
    notification.task_type = "unknown"
    with pytest.raises(ValidationError, match="Type de notification inconnu"):
        notification.clean()

    # pas de structure propriétaire
    notification.task_type = TaskType.ORPHAN_STRUCTURES
    notification.owner_structure = None
    with pytest.raises(ValidationError, match="Aucune structure attachée"):
        notification.clean()
    ...
