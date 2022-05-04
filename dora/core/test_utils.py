import random

from django.utils.crypto import get_random_string
from model_bakery import baker


def make_structure(**kwargs):
    siret = kwargs.pop("siret", None)
    if not siret:
        siret = get_random_string(14, "0123456789")
    latitude = kwargs.pop("latitude", None)
    if not latitude:
        latitude = random.random() * 90.0

    longitude = kwargs.pop("longitude", None)
    if not longitude:
        longitude = random.random() * 90.0
    return baker.make(
        "Structure", siret=siret, longitude=longitude, latitude=latitude, **kwargs
    )


def make_service(**kwargs):
    structure = kwargs.pop("structure") if "structure" in kwargs else make_structure()
    return baker.make("Service", structure=structure, **kwargs)
