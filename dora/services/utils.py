from django.contrib.gis.geos import Point


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
