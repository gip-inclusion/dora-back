from model_bakery import baker


def make_structure(**kwargs):
    return baker.make("Structure", _fill_optional=["siret"], **kwargs)


def make_service(**kwargs):
    structure = kwargs.pop("structure") if "structure" in kwargs else make_structure()
    return baker.make("Service", structure=structure, **kwargs)
