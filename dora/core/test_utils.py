import random

from django.utils.crypto import get_random_string
from model_bakery import baker


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
        "Structure", siret=siret, longitude=longitude, latitude=latitude, **kwargs
    )
    if user:
        structure.members.add(user)
    return structure


def make_service(**kwargs):
    structure = kwargs.pop("structure") if "structure" in kwargs else make_structure()
    return baker.make("Service", structure=structure, is_model=False, **kwargs)


def make_model(**kwargs):
    structure = kwargs.pop("structure") if "structure" in kwargs else make_structure()
    return baker.make("ServiceModel", structure=structure, is_model=True, **kwargs)
