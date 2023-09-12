import random

from django.utils import timezone
from django.utils.crypto import get_random_string
from model_bakery import baker

from dora.services.models import ServiceCategory, ServiceSubCategory
from dora.services.utils import update_sync_checksum


def make_user(structure=None, is_valid=True, is_admin=False, **kwargs):
    user = baker.make("users.User", is_valid=is_valid, **kwargs)
    if structure:
        structure.members.add(
            user,
            through_defaults={
                "is_admin": is_admin,
            },
        )

    return user


def make_structure(user=None, **kwargs):
    siret = kwargs.pop("siret", None)
    if not siret:
        siret = get_random_string(14, "0123456789")
    latitude = kwargs.pop("latitude", None)
    if not latitude:
        latitude = random.random() * 90.0

    longitude = kwargs.pop("longitude", None)
    if not longitude:
        longitude = random.random() * 90.0
    structure = baker.make(
        "Structure",
        siret=siret,
        longitude=longitude,
        latitude=latitude,
        modification_date=timezone.now(),
        **kwargs,
    )
    if user:
        structure.members.add(user)
    return structure


def make_service(**kwargs):
    structure = kwargs.pop("structure") if "structure" in kwargs else make_structure()
    categories = kwargs.pop("categories").split(",") if "categories" in kwargs else []
    subcategories = (
        kwargs.pop("subcategories").split(",") if "subcategories" in kwargs else []
    )
    modification_date = (
        kwargs.pop("modification_date") if "modification_date" in kwargs else None
    )

    service = baker.make(
        "Service",
        structure=structure,
        is_model=False,
        modification_date=modification_date if modification_date else timezone.now(),
        **kwargs,
    )
    if categories:
        service.categories.set(ServiceCategory.objects.filter(value__in=categories))
    if subcategories:
        service.subcategories.set(
            ServiceSubCategory.objects.filter(value__in=subcategories)
        )

    return service


def make_model(**kwargs):
    structure = kwargs.pop("structure") if "structure" in kwargs else make_structure()
    model = baker.make(
        "ServiceModel",
        structure=structure,
        is_model=True,
        modification_date=timezone.now(),
        **kwargs,
    )
    model.sync_checksum = update_sync_checksum(model)
    model.save()
    return model


def make_orientation(**kwargs):
    prescriber_structure = make_structure()
    prescriber = make_user(structure=prescriber_structure)
    orientation = baker.make(
        "Orientation",
        prescriber=prescriber,
        service=make_service(_fill_optional=["contact_email"]),
    )
    return orientation
