import pytest
from model_bakery import baker

from dora.admin_express.models import AdminDivisionType
from dora.core.test_utils import make_service, make_structure, make_user
from dora.services.enums import ServiceStatus


@pytest.fixture
def orphan_service():
    # service devant sortir lors d'une recherche globale
    service = make_service(
        status=ServiceStatus.PUBLISHED,
        diffusion_zone_type=AdminDivisionType.COUNTRY,
        # le résultat de `make_service` est maintenant rattaché à une structure "non-orpheline"
        # mais on veut ici un service "orphelin" par défaut
        structure=make_structure(),
    )
    return service


@pytest.fixture
def structure_with_user():
    return make_structure(user=make_user())


def test_search_services_with_orphan_structure(
    api_client, orphan_service, structure_with_user
):
    # les services rattachés à une structure orpheline
    # doivent être filtrés lors de la recherche

    # le paramètre `city` est nécessaire a minima
    city = baker.make("City")
    response = api_client.get(f"/search/?city={city.code}")

    assert response.status_code == 200
    assert not response.data[
        "services"
    ], "aucun service ne devrait être retourné (structure orpheline)"

    # on ajoute une structure avec un utilisateur au service
    orphan_service.structure = structure_with_user
    orphan_service.save()
    response = api_client.get(f"/search/?city={city.code}")

    assert response.status_code == 200
    assert response.data[
        "services"
    ], "un service devrait être retourné (structure avec utilisateur)"

    [found] = response.data["services"]

    assert found["slug"] == orphan_service.slug
