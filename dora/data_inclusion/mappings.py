from dora.services.enums import ServiceStatus

DI_TO_DORA_DIFFUSION_ZONE_TYPE_MAPPING = {
    "commune": "city",
    "epci": "epci",
    "departement": "department",
    "region": "region",
    "pays": "country",
}


def map_search_result(result: dict) -> dict:
    # On transforme les champs nécessaires à l'affichage des resultats de recherche au format DORA
    # (c.a.d qu'on veut un objet similaire à ce que renvoie le SearchResultSerializer)
    location_str = ""
    if result["service"]["modes_accueil"]:
        if "en-presentiel" in result["service"]["modes_accueil"]:
            location_str = (
                f"{result['service']['code_postal']} {result['service']['commune']}"
            )
        elif "a-distance" in result["service"]["modes_accueil"]:
            location_str = "À distance"

    return {
        "diffusion_zone_type": DI_TO_DORA_DIFFUSION_ZONE_TYPE_MAPPING.get(
            result["service"]["zone_diffusion_type"], None
        ),
        "distance": result["distance"] or 0,  # en km
        "location": location_str,
        # TODO: spécifier 'en-presentiel' si on a une geoloc/adresse?
        "location_kinds": result["service"]["modes_accueil"] or [],
        "modification_date": result["service"]["date_maj"],
        "name": result["service"]["nom"],
        "short_desc": result["service"]["presentation_resume"],
        "slug": f"{result['service']['source']}--{result['service']['id']}",
        "status": ServiceStatus.PUBLISHED,
        "structure": "",
        "structure_info": {"name": result["service"]["structure"]["nom"]},
        # Champs spécifiques aux résultats d·i
        "type": "di",
        "source": result["service"]["source"],
        "id": result["service"]["id"],
    }


def map_service(service: dict) -> dict:
    # todo: categories/subcategories

    return {
        "name": service["nom"],
        "structureInfo": {
            "name": service["structure"]["nom"],
        },
        "subcategories": [],
        "concerned_public_display": [],
        "access_conditions_display": [],
        "requirements_display": [],
        "coach_orientation_modes_display": [],
        "beneficiaries_access_modes_display": [],
        "forms_info": [],
        "credentials_display": [],
        "shortDesc": service["presentation_resume"],
        "fullDesc": service["presentation_detail"],
        "kinds": service["types"],
        "kinds_display": service["types"] or [],
    }
