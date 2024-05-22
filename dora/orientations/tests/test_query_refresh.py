import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from freezegun import freeze_time

from dora.core.test_utils import make_orientation

from ..models import ORIENTATION_QUERY_LINK_TTL_DAY, Orientation


@pytest.fixture
def orientation() -> Orientation:
    return make_orientation()


def test_query_expires_at(orientation):
    assert not orientation.query_expired

    # pas de refresh si pas expiré
    h = orientation.get_query_id_hash()
    orientation.refresh_query_expiration_date()
    assert h == orientation.get_query_id_hash()

    with freeze_time(
        time_to_freeze=timezone.now()
        + relativedelta(days=ORIENTATION_QUERY_LINK_TTL_DAY)
    ):
        assert orientation.query_expired


def test_query_refresh(api_client, orientation):
    url = f"/orientations/{orientation.query_id}/refresh/"
    response = api_client.patch(url, follow=True)

    assert response.status_code == 204


def test_query_access(api_client, orientation):
    url = f"/orientations/{orientation.query_id}/"
    response = api_client.get(url, follow=True)

    # permissions : pas de hash, pas d'orientation (pseudo-auth)
    assert response.status_code == 401

    url += f"?h={orientation.get_query_id_hash()}"
    response = api_client.get(url, follow=True)

    assert response.status_code == 200
