import random

from django.utils import timezone
from django.utils.crypto import get_random_string
from model_bakery import baker

from dora.services.utils import update_sync_checksum


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
    return baker.make(
        "Service",
        structure=structure,
        is_model=False,
        modification_date=timezone.now(),
        **kwargs,
    )


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
