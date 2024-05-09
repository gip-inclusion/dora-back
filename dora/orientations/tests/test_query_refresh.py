import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from freezegun import freeze_time

from dora.core.test_utils import make_orientation

from ..models import Orientation


@pytest.fixture
def orientation() -> Orientation:
    return make_orientation()


def test_query_expires_at(orientation):
    assert not orientation.query_expired

    # pas de refresh si pas expiré
    h = orientation.get_query_id_hash()
    orientation.refresh_query_expiration_date()
    assert h == orientation.get_query_id_hash()

    with freeze_time(time_to_freeze=timezone.now() + relativedelta(days=8)):
        assert orientation.query_expired


def test_query_refresh(api_client, orientation):
    url = f"/orientations/{orientation.query_id}/refresh/"
    response = api_client.patch(url, follow=True)

    # permissions
    assert response.status_code == 401

    api_client.force_authenticate(user=orientation.prescriber)
    response = api_client.patch(url, follow=True)

    assert response.status_code == 204


def test_query_check(api_client, orientation):
    url = f"/orientations/{orientation.query_id}/check/?h="
    response = api_client.get(url, follow=True)

    # l'API réponds toujours
    assert response.status_code == 200
    # hash non fourni
    assert response.json().get("result") == "invalid"

    # hash fourni mais incorrect : on considère le lien comme expiré
    response = api_client.get(url + "xxxxxx", follow=True)
    assert response.status_code == 200
    assert response.json().get("result") == "expired"

    # hash correct, on retourne l'identifiant de query
    response = api_client.get(url + orientation.get_query_id_hash(), follow=True)
    assert response.status_code == 200
    assert response.json().get("result") == str(orientation.query_id)
