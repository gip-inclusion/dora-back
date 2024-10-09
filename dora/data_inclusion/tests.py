from .constants import THEMATIQUES_MAPPING_DI_TO_DORA, THEMATIQUES_MAPPING_DORA_TO_DI
from .mappings import map_service
from .test_utils import FakeDataInclusionClient, make_di_service_data


def test_map_service_thematiques_mapping():
    input_thematiques = [
        "logement-hebergement",
        "logement-hebergement--connaissance-de-ses-droits-et-interlocuteurs",
        "logement-hebergement--besoin-dadapter-mon-logement",
    ] + list(THEMATIQUES_MAPPING_DI_TO_DORA.keys())

    expected_categories = ["logement-hebergement"]
    expected_subcategories = [
        "logement-hebergement--connaissance-de-ses-droits-et-interlocuteurs",
        "logement-hebergement--besoin-dadapter-mon-logement",
    ] + list(THEMATIQUES_MAPPING_DI_TO_DORA.values())

    di_service_data = make_di_service_data(thematiques=input_thematiques)
    service = map_service(di_service_data, False)

    assert sorted(service["categories"]) == sorted(expected_categories)
    assert sorted(service["subcategories"]) == sorted(expected_subcategories)


def test_di_client_search_thematiques_mapping():
    input_thematique = list(THEMATIQUES_MAPPING_DORA_TO_DI.keys())[0]
    output_thematique = list(THEMATIQUES_MAPPING_DORA_TO_DI.values())[0][0]

    di_client = FakeDataInclusionClient()
    di_service_data = make_di_service_data(thematiques=[output_thematique])
    di_client.services.append(di_service_data)

    results = di_client.search_services(thematiques=[input_thematique])

    assert len(results) == 1
