import hashlib

from django.db.models import Q
from django.shortcuts import get_object_or_404

from dora.admin_express.models import EPCI, AdminDivisionType, City, Department, Region
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
            & Q(diffusion_zone_details__in=city.epcis)
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


def filter_services_by_department(services, dept_code):
    department = get_object_or_404(Department, pk=dept_code)

    return services.filter(
        Q(diffusion_zone_type=AdminDivisionType.COUNTRY)
        | (
            Q(diffusion_zone_type=AdminDivisionType.CITY)
            & Q(diffusion_zone_details__in=City.objects.filter(department=dept_code))
        )
        | (
            Q(diffusion_zone_type=AdminDivisionType.EPCI)
            & Q(
                diffusion_zone_details__in=EPCI.objects.filter(
                    departments__contains=[dept_code]
                )
            )
        )
        | (
            Q(diffusion_zone_type=AdminDivisionType.DEPARTMENT)
            & Q(diffusion_zone_details=department.code)
        )
        | (
            Q(diffusion_zone_type=AdminDivisionType.REGION)
            & Q(diffusion_zone_details=department.region)
        )
    )


def filter_services_by_region(services, region_code):
    region = get_object_or_404(Region, pk=region_code)

    return services.filter(
        Q(diffusion_zone_type=AdminDivisionType.COUNTRY)
        | (
            Q(diffusion_zone_type=AdminDivisionType.CITY)
            & Q(diffusion_zone_details__in=City.objects.filter(region=region_code))
        )
        | (
            Q(diffusion_zone_type=AdminDivisionType.EPCI)
            & Q(
                diffusion_zone_details__in=EPCI.objects.filter(
                    regions__contains=[region_code]
                )
            )
        )
        | (
            Q(diffusion_zone_type=AdminDivisionType.DEPARTMENT)
            & Q(
                diffusion_zone_details__in=Department.objects.filter(region=region_code)
            )
        )
        | (
            Q(diffusion_zone_type=AdminDivisionType.REGION)
            & Q(diffusion_zone_details=region.code)
        )
    )
