from django.utils import dateparse, timezone

from dora.admin_express.models import AdminDivisionType
from dora.core.utils import code_insee_to_code_dept
from dora.services.enums import ServiceStatus
from dora.services.models import (
    LocationKind,
    ServiceCategory,
    ServiceKind,
    ServiceSubCategory,
    get_diffusion_zone_details_display,
    get_update_status,
)

DI_TO_DORA_DIFFUSION_ZONE_TYPE_MAPPING = {
    "commune": "city",
    "epci": "epci",
    "departement": "department",
    "region": "region",
    "pays": "country",
}


# TODO:
# On pourrait avoir envie d'instancier un objet service et de réutiliser la sérialisation implémentée.
# Les relations m2m nécessitent malheureusement la sauvegarde en db.
# On pourrait tout de même implémenter les mappings avec des serializers basés sur ceux existants.


def map_search_result(result: dict) -> dict:
    # On transforme les champs nécessaires à l'affichage des resultats de recherche au format DORA
    # (c.a.d qu'on veut un objet similaire à ce que renvoie le SearchResultSerializer)

    service_data = result["service"]

    location_str = ""
    if service_data["modes_accueil"]:
        if "en-presentiel" in service_data["modes_accueil"]:
            location_str = f"{service_data['code_postal']} {service_data['commune']}"
        elif "a-distance" in service_data["modes_accueil"]:
            location_str = "À distance"

    return {
        #
        # SearchResultSerializer
        #
        "distance": result["distance"] or 0,  # en km
        "location": location_str,
        #
        # ServiceListSerializer
        #
        "structure_info": {"name": service_data["structure"]["nom"]},
        #
        # ServiceSerializer
        #
        # TODO: spécifier 'en-presentiel' si on a une geoloc/adresse?
        "location_kinds": service_data["modes_accueil"] or [],
        "modification_date": service_data["date_maj"],
        "name": service_data["nom"],
        "short_desc": service_data["presentation_resume"] or "",
        "slug": f"{service_data['source']}--{service_data['id']}",
        "status": ServiceStatus.PUBLISHED.value,
        "structure": "",
        # Champs spécifiques aux résultats d·i
        "type": "di",
        "source": service_data["source"],
        "id": service_data["id"],
        "diffusion_zone_type": DI_TO_DORA_DIFFUSION_ZONE_TYPE_MAPPING.get(
            result["service"]["zone_diffusion_type"], None
        ),
    }


def map_service(service_data: dict) -> dict:
    categories = []
    subcategories = []
    if service_data["thematiques"] is not None:
        categories = ServiceCategory.objects.filter(
            value__in=service_data["thematiques"]
        )
        subcategories = ServiceSubCategory.objects.filter(
            value__in=service_data["thematiques"]
        )

    location_kinds = []
    if service_data["modes_accueil"] is not None:
        location_kinds = LocationKind.objects.filter(
            value__in=service_data["modes_accueil"]
        )

    kinds = []
    if service_data["types"] is not None:
        kinds = ServiceKind.objects.filter(value__in=service_data["types"])

    zone_diffusion_type = DI_TO_DORA_DIFFUSION_ZONE_TYPE_MAPPING.get(
        service_data["zone_diffusion_type"], None
    )

    department = None
    if service_data["code_insee"] is not None:
        department = code_insee_to_code_dept(service_data["code_insee"])

    update_status = None
    if service_data["date_maj"] is not None:
        update_status = get_update_status(
            status=ServiceStatus.PUBLISHED,
            modification_date=timezone.make_aware(
                dateparse.parse_datetime(service_data["date_maj"])
            ),
        ).value

    credentials = []
    if service_data["justificatifs"] not in [None, ""]:
        credentials = service_data["justificatifs"].split(",")

    fee_condition = None
    if service_data["frais"] is not None:
        fee_condition = ", ".join(service_data["frais"])

    requirements = []
    if service_data["pre_requis"] not in [None, ""]:
        requirements = service_data["pre_requis"].split(",")

    return {
        "access_conditions": [],
        "access_conditions_display": [],
        "address1": service_data["adresse"],
        "address2": service_data["complement_adresse"],
        "beneficiaries_access_modes": service_data["modes_orientation_beneficiaire"]
        or [],
        "beneficiaries_access_modes_display": service_data[
            "modes_orientation_beneficiaire"
        ]
        or [],
        "beneficiaries_access_modes_other": None,
        "can_write": False,
        "categories": [c.value for c in categories],
        "categories_display": [c.label for c in categories],
        "category": categories[0].value if len(categories) > 0 else None,
        "category_display": categories[0].label if len(categories) > 0 else None,
        "city": service_data["commune"],
        "city_code": service_data["code_insee"],
        "coach_orientation_modes": service_data["modes_orientation_accompagnateur"]
        or [],
        "coach_orientation_modes_display": service_data[
            "modes_orientation_accompagnateur"
        ]
        or [],
        "coach_orientation_modes_other": None,
        "concerned_public": service_data["profils"] or [],
        "concerned_public_display": service_data["profils"] or [],
        "contact_email": service_data["courriel"],
        "contact_name": service_data["contact_nom_prenom"],
        "contact_phone": service_data["telephone"],
        "creation_date": service_data["date_creation"],
        "credentials": credentials,
        "credentials_display": credentials,
        "department": department,
        "diffusion_zone_details": service_data["zone_diffusion_code"],
        "diffusion_zone_details_display": get_diffusion_zone_details_display(
            diffusion_zone_details=service_data["zone_diffusion_code"],
            diffusion_zone_type=zone_diffusion_type,
        ),
        "diffusion_zone_type": zone_diffusion_type,
        "diffusion_zone_type_display": AdminDivisionType(zone_diffusion_type).label
        if zone_diffusion_type is not None
        else "",
        "fee_condition": fee_condition,
        "fee_details": service_data["frais_autres"] or "",
        "forms": [],
        "forms_info": [],
        "full_desc": service_data["presentation_detail"] or "",
        "geom": None,
        "has_already_been_unpublished": None,
        "is_available": True,
        "is_contact_info_public": service_data["contact_public"],
        "is_cumulative": service_data["cumulable"],
        "kinds": [k.value for k in kinds],
        "kinds_display": [k.label for k in kinds],
        "location_kinds": [lk.value for lk in location_kinds],
        "location_kinds_display": [lk.label for lk in location_kinds],
        "model": None,
        "model_changed": None,
        "model_name": None,
        "modification_date": service_data["date_maj"],
        "name": service_data["nom"],
        "online_form": None,
        "postal_code": service_data["code_postal"],
        "publication_date": None,
        "qpv_or_zrr": None,
        "recurrence": service_data["recurrence"],
        "remote_url": None,
        "requirements": requirements,
        "requirements_display": requirements,
        "short_desc": service_data["presentation_resume"] or "",
        "slug": f"{service_data['source']}--{service_data['id']}",
        "status": ServiceStatus.PUBLISHED.value,
        "structure": None,
        "structure_info": {
            "name": service_data["structure"]["nom"],
        },
        "subcategories": [c.value for c in subcategories],
        "subcategories_display": [c.label for c in subcategories],
        "suspension_date": service_data["date_suspension"],
        "update_status": update_status,
        "use_inclusion_numerique_scheme": False,
    }
