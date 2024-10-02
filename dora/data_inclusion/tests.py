from .constants import THEMATIQUES_MAPPING_DI_TO_DORA
from .mappings import map_service
from .test_utils import make_di_service_data


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

    assert set(service["categories"]) == set(expected_categories)
    assert set(service["subcategories"]) == set(expected_subcategories)
