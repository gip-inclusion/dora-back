from django.contrib.gis.geos import Point
from django.db.models import Q
from django.shortcuts import get_object_or_404

from dora.admin_express.models import AdminDivisionType, City  # , Department, Region
from dora.admin_express.utils import arrdt_to_main_insee_code


def _duplicate_customizable_choices(field, choices, structure):
    for choice in choices:
        if choice.structure:
            new_choice, _created = choice._meta.model.objects.get_or_create(
                name=choice.name, structure=structure
            )
            field.add(new_choice)
        else:
            field.add(choice)


def copy_service(service, structure, user):
    clone = service.__class__.objects.get(pk=service.pk)
    clone.id = None  # Duplique l'instance

    clone.slug = None
    clone.contact_name = ""
    clone.contact_phone = ""
    clone.contact_email = ""
    clone.is_contact_info_public = False

    clone.structure = structure
    clone.address1 = structure.address1
    clone.address2 = structure.address2
    clone.postal_code = structure.postal_code
    clone.city_code = structure.city_code
    clone.city = structure.city
    if structure.longitude and structure.latitude:
        clone.geom = Point(structure.longitude, structure.latitude, srid=4326)
    else:
        clone.geom = None

    clone.diffusion_zone_type = ""
    clone.diffusion_zone_details = ""
    clone.suspension_date = None

    clone.is_draft = True
    clone.is_model = False

    clone.creation_date = None
    clone.modification_date = None
    clone.publication_date = None
    clone.last_editor = user
    clone.model = service
    clone.save()

    # Restaure les champs M2M
    # EnumModels
    clone.kinds.set(service.kinds.all())
    clone.categories.set(service.categories.all())
    clone.subcategories.set(service.subcategories.all())
    clone.beneficiaries_access_modes.set(service.beneficiaries_access_modes.all())
    clone.coach_orientation_modes.set(service.coach_orientation_modes.all())
    # NB: exclut volontairement le champ location_kinds

    # CustomizableChoice
    _duplicate_customizable_choices(
        clone.access_conditions, service.access_conditions.all(), structure
    )
    _duplicate_customizable_choices(
        clone.concerned_public, service.concerned_public.all(), structure
    )
    _duplicate_customizable_choices(
        clone.requirements, service.requirements.all(), structure
    )
    _duplicate_customizable_choices(
        clone.credentials, service.credentials.all(), structure
    )

    return clone


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
