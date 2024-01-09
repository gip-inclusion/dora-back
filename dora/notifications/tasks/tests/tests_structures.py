from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone
from freezegun import freeze_time

from dora.core.test_utils import make_structure
from dora.notifications.enums import NotificationStatus, TaskType
from dora.notifications.models import Notification

from ..core import Task
from ..structures import OrphanStructuresTask

# note : le test des méthodes `candidates` peut aussi être fait au niveau
# du modèle propriétaire si la méthode consiste en un simple queryset.
# Dans le cas contraire, on peut éventuellement ajouter des tests ici.
# pas utile pour les structures orphelines en tout cas.


@pytest.fixture
def orphan_structure_task():
    return OrphanStructuresTask()


def test_orphan_structures_registered():
    assert OrphanStructuresTask in Task.registered_tasks()


def test_orphan_structure_test_should_trigger(orphan_structure_task):
    # créée telle quelle, une structure est orpheline
    make_structure(email="test@test.com")

    print("k", orphan_structure_task._model_key)

    ok, _, _ = orphan_structure_task.run()
    n = Notification.objects.pending().first()

    # premier déclenchement immédiatement
    assert ok
    assert n.task_type == TaskType.ORPHAN_STRUCTURES
    assert n.counter == 1

    ok, _, _ = orphan_structure_task.run()
    n = Notification.objects.pending().first()

    # plus rien à traiter maitenant
    assert not ok

    for in_weeks in (2, 4, 6):
        # déclenchements toutes les 2 semaines
        with freeze_time(timezone.now() + timedelta(weeks=in_weeks)):
            ok, _, _ = orphan_structure_task.run()
            expected_count = 1 + in_weeks / 2
            n.refresh_from_db()

            # la notification a bien été déclenchée
            assert ok
            assert n.counter == expected_count

            ok, _, _ = orphan_structure_task.run()
            n.refresh_from_db()

            # à la même date :
            # une nouvelle exécution ne déclenche pas de nouvelle notification
            assert not ok
            assert n.counter == expected_count

    # à ce point la seule notification doit être clôturée
    assert len(Notification.objects.pending()) == 0
    assert n.status == NotificationStatus.COMPLETE

    ok, _, _ = orphan_structure_task.run()

    assert not ok


def test_process_orphan_structures(orphan_structure_task):
    structure = make_structure(email="jessie@pixar.com")

    ok, _, _ = orphan_structure_task.run()

    assert ok == 1

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [structure.email]

    # des tests plus complets concernant la structure et le contenu de l'email
    # sont effectués dans le module `dora.structures.tests.test_emails`
