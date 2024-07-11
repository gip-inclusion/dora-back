import pytest
from model_bakery import baker

from dora.admin_express.models import AdminDivisionType
from dora.core.test_utils import make_service, make_structure, make_user
from dora.services.enums import ServiceStatus


@pytest.fixture
def service():
    # service devant sortir lors d'une recherche globale
    service = make_service(
        status=ServiceStatus.PUBLISHED,
        diffusion_zone_type=AdminDivisionType.COUNTRY,
    )
    return service


@pytest.fixture
def structure_with_user():
    return make_structure(user=make_user())


def test_search_services_with_orphan_structure(
    api_client, service, structure_with_user
):
    # les services rattachés à une structure orpheline
    # doivent être filtrés lors de la recherche

    # le paramètre `city` est nécessaire a minima
    city = baker.make("City")
    response = api_client.get(f"/search/?city={city.code}")

    assert response.status_code == 200
    assert not response.data[
        "services"
    ], "aucun service ne devrait être trouvé (structure orpheline)"

    # on ajoute une structure au service
    service.structure = structure_with_user
    service.save()
    response = api_client.get(f"/search/?city={city.code}")

    assert response.status_code == 200
    assert response.data[
        "services"
    ], "un service ne devrait être trouvé (structure avec utilisateur)"

    [found] = response.data["services"]

    assert found["slug"] == service.slug
