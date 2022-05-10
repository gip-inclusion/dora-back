import hashlib

from django.contrib.gis.geos import Point
from django.db.models import Q
from django.shortcuts import get_object_or_404

from dora.admin_express.models import AdminDivisionType, City  # , Department, Region
from dora.admin_express.utils import arrdt_to_main_insee_code

SYNC_FIELDS = [
    "name",
    "short_desc",
    "full_desc",
    "is_cumulative",
    "has_fee",
    "fee_details",
    "beneficiaries_access_modes_other",
    "coach_orientation_modes_other",
    "forms",
    "online_form",
    "contact_name",
    "contact_phone",
    "contact_email",
    "is_contact_info_public",
    "remote_url",
    "diffusion_zone_details",
    "qpv_or_zrr",
    "recurrence",
]

SYNC_M2M_FIELDS = [
    "kinds",
    "categories",
    "subcategories",
    "beneficiaries_access_modes",
    "coach_orientation_modes",
]

SYNC_CUSTOM_M2M_FIELDS = [
    "access_conditions",
    "concerned_public",
    "requirements",
    "credentials",
]


def _duplicate_customizable_choices(field, choices, structure):
    # TODO add tests
    for choice in choices:
        if choice.structure:
            new_choice, _created = choice._meta.model.objects.get_or_create(
                name=choice.name, structure=structure
            )
            field.add(new_choice)
        else:
            field.add(choice)


def update_sync_checksum(service):
    md5 = hashlib.md5(usedforsecurity=False)
    for field in SYNC_FIELDS:
        md5.update(repr(getattr(service, field)).encode())
    for m2m_field in [*SYNC_M2M_FIELDS, *SYNC_CUSTOM_M2M_FIELDS]:
        md5.update(
            repr(
                list(
                    getattr(service, m2m_field)
                    .all()
                    .values_list("pk", flat=True)
                    .order_by("pk")
                )
            ).encode()
        )

    result = md5.hexdigest()
    return result


def copy_service(original, structure, user):
    service = original.__class__.objects.create(structure=structure)

    for field in SYNC_FIELDS:
        setattr(service, field, getattr(original, field))

    # Overwrite address, to default to the new structure one
    service.address1 = structure.address1
    service.address2 = structure.address2
    service.postal_code = structure.postal_code
    service.city_code = structure.city_code
    service.city = structure.city
    if structure.longitude and structure.latitude:
        service.geom = Point(structure.longitude, structure.latitude, srid=4326)
    else:
        service.geom = None

    # Metadata
    service.is_draft = True
    service.is_model = False
    service.creator = original.creator
    service.last_editor = user
    service.model = original
    service.last_sync_checksum = original.sync_checksum

    # Restaure les champs M2M
    for field in SYNC_M2M_FIELDS:
        getattr(service, field).set(getattr(original, field).all())

    for field in SYNC_CUSTOM_M2M_FIELDS:
        _duplicate_customizable_choices(
            getattr(service, field), getattr(original, field).all(), service.structure
        )

    service.save()
    return service


def sync_service(service, user, fields):
    original = service.model

    # Sync'd Simple fields
    for field in set(SYNC_FIELDS) & set(fields):
        setattr(service, field, getattr(original, field))

    # Restaure les champs M2M
    for field in set(SYNC_M2M_FIELDS) & set(fields):
        getattr(service, field).set(getattr(original, field).all())

    for field in set(SYNC_CUSTOM_M2M_FIELDS) & set(fields):
        _duplicate_customizable_choices(
            getattr(service, field), getattr(original, field).all(), service.structure
        )

    service.last_editor = user
    service.last_sync_checksum = original.sync_checksum
    service.save()


def get_service_diffs(service):
    original = service.model
    result = {}
    for field in SYNC_FIELDS:
        current = getattr(service, field)
        source = getattr(original, field)
        if current != source:
            result[field] = {"parent": source, "current": current}

    for field in SYNC_M2M_FIELDS:
        current = set(getattr(service, field).all())
        source = set(getattr(original, field).all())
        if current != source:
            result[field] = {
                "parent": [{"value": v.value, "label": v.label} for v in source],
                "current": [{"value": v.value, "label": v.label} for v in current],
            }

    for field in SYNC_CUSTOM_M2M_FIELDS:
        current = set(getattr(service, field).all())
        source = set(getattr(original, field).all())
        if current != source:
            result[field] = {
                "parent": [{"value": v.pk, "label": v.name} for v in source],
                "current": [{"value": v.pk, "label": v.name} for v in current],
            }

    return result


def filter_services_by_city_code(services, city_code):
    # Si la requete entrante contient un code insee d'arrondissement
    # on le converti pour récupérer le code de la commune entière
    city_code = arrdt_to_main_insee_code(city_code)
    city = get_object_or_404(City, pk=city_code)

    return services.filter(
        Q(diffusion_zone_type=AdminDivisionType.COUNTRY)
        | (
            Q(diffusion_zone_type=AdminDivisionType.CITY)
            & Q(diffusion_zone_details=city.code)
        )
        | (
            Q(diffusion_zone_type=AdminDivisionType.EPCI)
            & Q(diffusion_zone_details__in=city.epci.split("/"))
        )
        | (
            Q(diffusion_zone_type=AdminDivisionType.DEPARTMENT)
            & Q(diffusion_zone_details=city.department)
        )
        | (
            Q(diffusion_zone_type=AdminDivisionType.REGION)
            & Q(diffusion_zone_details=city.region)
        )
    )


# def filter_services_by_department(services, dept_code):
#     department = get_object_or_404(Department, pk=dept_code)

#     return services.filter(
#         Q(diffusion_zone_type=AdminDivisionType.COUNTRY)
#         | (
#             Q(diffusion_zone_type=AdminDivisionType.DEPARTMENT)
#             & Q(diffusion_zone_details=department.code)
#         )
#         | (
#             Q(diffusion_zone_type=AdminDivisionType.REGION)
#             & Q(diffusion_zone_details=department.region)
#         )
#     )


# def filter_services_by_region(services, region_code):
#     region = get_object_or_404(Region, pk=region_code)

#     return services.filter(
#         Q(diffusion_zone_type=AdminDivisionType.COUNTRY)
#         | (
#             Q(diffusion_zone_type=AdminDivisionType.REGION)
#             & Q(diffusion_zone_details=region.code)
#         )
#     )
