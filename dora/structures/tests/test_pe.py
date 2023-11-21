from io import StringIO

from django.core.management import call_command
from django.utils.crypto import get_random_string
from model_bakery import baker

from dora.core.constants import SIREN_POLE_EMPLOI
from dora.core.test_utils import make_service, make_structure
from dora.structures.models import Structure


def make_fake_pe_siret():
    return SIREN_POLE_EMPLOI + get_random_string(5, "0123456789")


def make_pe_struct(*args, **kwargs):
    return make_structure(siret=make_fake_pe_siret(), *args, **kwargs)


def run_clean_pe_cmd():
    call_command("clean_orphan_pe_agencies", stdout=StringIO())


def test_empty_pe_struct_will_be_cleaned(api_client):
    assert Structure.objects.filter(siret__startswith=SIREN_POLE_EMPLOI).count() == 0
    make_pe_struct()
    assert Structure.objects.filter(siret__startswith=SIREN_POLE_EMPLOI).count() == 1
    run_clean_pe_cmd()
    assert Structure.objects.filter(siret__startswith=SIREN_POLE_EMPLOI).count() == 0


def test_pe_struct_with_members_wont_be_cleaned(api_client):
    assert Structure.objects.filter(siret__startswith=SIREN_POLE_EMPLOI).count() == 0
    user = baker.make("users.User", is_valid=True)
    make_pe_struct(user=user)
    assert Structure.objects.filter(siret__startswith=SIREN_POLE_EMPLOI).count() == 1
    run_clean_pe_cmd()
    assert Structure.objects.filter(siret__startswith=SIREN_POLE_EMPLOI).count() == 1


def test_pe_struct_with_potential_members_wont_be_cleaned(api_client):
    assert Structure.objects.filter(siret__startswith=SIREN_POLE_EMPLOI).count() == 0
    user = baker.make("users.User", is_valid=True)
    struct = make_pe_struct()
    baker.make("StructurePutativeMember", structure=struct, user=user)
    assert Structure.objects.filter(siret__startswith=SIREN_POLE_EMPLOI).count() == 1
    run_clean_pe_cmd()
    assert Structure.objects.filter(siret__startswith=SIREN_POLE_EMPLOI).count() == 1


def test_pe_struct_with_services_wont_be_cleaned(api_client):
    assert Structure.objects.filter(siret__startswith=SIREN_POLE_EMPLOI).count() == 0
    struct = make_pe_struct()
    make_service(structure=struct)
    assert Structure.objects.filter(siret__startswith=SIREN_POLE_EMPLOI).count() == 1
    run_clean_pe_cmd()
    assert Structure.objects.filter(siret__startswith=SIREN_POLE_EMPLOI).count() == 1
