from django.utils.crypto import get_random_string
from model_bakery import baker


def make_structure(**kwargs):
    siret = kwargs.pop("siret", "")
    if not siret:
        siret = get_random_string(14, "0123456789")
    return baker.make("Structure", siret=siret, **kwargs)


def make_service(**kwargs):
    structure = kwargs.pop("structure") if "structure" in kwargs else make_structure()
    return baker.make("Service", structure=structure, **kwargs)
