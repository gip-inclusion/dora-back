from django.contrib.auth import authenticate
from model_bakery import baker
from rest_framework.test import APITestCase

from dora.structures.models import (
    Structure,
    StructureMember,
    StructurePutativeMember,
    StructureTypology,
)
from dora.users.models import User


class AuthTestCase(APITestCase):
    # Registration
    def test_register_new_user_and_struct_creates_user(self):
        self.client.force_authenticate(user=None)
        establishment = baker.make("Establishment", siret="12345678901234")
        data = {
            "first_name": "Foo",
            "last_name": "Bar",
            "email": "foo@bar.com",
            "password": "lkqjfl123!)p",
            "siret": establishment.siret,
        }
        response = self.client.post("/auth/register-structure-and-user/", data)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(email="foo@bar.com").exists())
        self.assertFalse(User.objects.get(email="foo@bar.com").is_valid)
        self.assertIsNotNone(authenticate(email="foo@bar.com", password="lkqjfl123!)p"))

    def test_register_new_user_and_struct_creates_structure_if_needed(self):
        self.client.force_authenticate(user=None)
        establishment = baker.make("Establishment", siret="12345678901234")
        data = {
            "first_name": "Foo",
            "last_name": "Bar",
            "email": "foo@bar.com",
            "password": "lkqjfl123!)p",
            "siret": establishment.siret,
        }
        response = self.client.post("/auth/register-structure-and-user/", data)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Structure.objects.filter(siret=establishment.siret).exists())

    def test_register_new_user_and_struct_uses_existing_structure(self):
        self.client.force_authenticate(user=None)
        establishment = baker.make("Establishment", siret="12345678901234")
        baker.make("Structure", siret=establishment.siret)
        data = {
            "first_name": "Foo",
            "last_name": "Bar",
            "email": "foo@bar.com",
            "password": "lkqjfl123!)p",
            "siret": establishment.siret,
        }
        response = self.client.post("/auth/register-structure-and-user/", data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Structure.objects.filter(siret=establishment.siret).count(), 1)

    def test_register_new_user_and_struct_first_user_becomes_admin(self):
        self.client.force_authenticate(user=None)
        establishment = baker.make("Establishment", siret="12345678901234")
        data = {
            "first_name": "Foo",
            "last_name": "Bar",
            "email": "foo@bar.com",
            "password": "lkqjfl123!)p",
            "siret": establishment.siret,
        }
        response = self.client.post("/auth/register-structure-and-user/", data)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(StructureMember.objects.get(user__email="foo@bar.com").is_admin)

    def test_register_new_user_and_struct_first_user_dont_need_admin_validation(self):
        self.client.force_authenticate(user=None)
        establishment = baker.make("Establishment", siret="12345678901234")
        data = {
            "first_name": "Foo",
            "last_name": "Bar",
            "email": "foo@bar.com",
            "password": "lkqjfl123!)p",
            "siret": establishment.siret,
        }
        response = self.client.post("/auth/register-structure-and-user/", data)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(StructureMember.objects.get(user__email="foo@bar.com"))

    def test_register_new_user_and_struct_first_user_becomes_admin_when_no_admin(self):
        self.client.force_authenticate(user=None)
        establishment = baker.make("Establishment", siret="12345678901234")
        structure = baker.make("Structure", siret=establishment.siret)
        baker.make(
            StructureMember,
            structure=structure,
            is_admin=False,
            user__is_valid=True,
        )
        data = {
            "first_name": "Foo",
            "last_name": "Bar",
            "email": "foo@bar.com",
            "password": "lkqjfl123!)p",
            "siret": establishment.siret,
        }
        response = self.client.post("/auth/register-structure-and-user/", data)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(StructureMember.objects.get(user__email="foo@bar.com").is_admin)

    def test_register_new_user_and_struct_first_user_dont_need_admin_validation_when_no_admin(
        self,
    ):
        self.client.force_authenticate(user=None)
        establishment = baker.make("Establishment", siret="12345678901234")
        data = {
            "first_name": "Foo",
            "last_name": "Bar",
            "email": "foo@bar.com",
            "password": "lkqjfl123!)p",
            "siret": establishment.siret,
        }
        response = self.client.post("/auth/register-structure-and-user/", data)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(StructureMember.objects.get(user__email="foo@bar.com"))

    def test_register_new_user_and_struct_following_users_dont_become_admin(self):
        self.client.force_authenticate(user=None)
        establishment = baker.make("Establishment", siret="12345678901234")
        structure = baker.make("Structure", siret=establishment.siret)
        baker.make(
            StructureMember,
            structure=structure,
            is_admin=True,
            user__is_valid=True,
        )
        data = {
            "first_name": "Foo",
            "last_name": "Bar",
            "email": "foo@bar.com",
            "password": "lkqjfl123!)p",
            "siret": establishment.siret,
        }
        response = self.client.post("/auth/register-structure-and-user/", data)
        self.assertEqual(response.status_code, 201)
        self.assertFalse(
            StructurePutativeMember.objects.get(user__email="foo@bar.com").is_admin
        )

    def test_register_new_user_and_struct_following_users_need_admin_validation(self):
        self.client.force_authenticate(user=None)
        establishment = baker.make("Establishment", siret="12345678901234")
        structure = baker.make("Structure", siret=establishment.siret)
        baker.make(
            StructureMember,
            structure=structure,
            is_admin=True,
            user__is_valid=True,
        )
        data = {
            "first_name": "Foo",
            "last_name": "Bar",
            "email": "foo@bar.com",
            "password": "lkqjfl123!)p",
            "siret": establishment.siret,
        }
        response = self.client.post("/auth/register-structure-and-user/", data)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            StructurePutativeMember.objects.filter(
                user__email="foo@bar.com", is_admin=False, invited_by_admin=False
            ).exists()
        )
        self.assertFalse(
            StructureMember.objects.filter(user__email="foo@bar.com").exists()
        )

    def test_register_new_user_and_struct_first_non_staff_becomes_admin(self):
        self.client.force_authenticate(user=None)
        establishment = baker.make("Establishment", siret="12345678901234")
        structure = baker.make("Structure", siret=establishment.siret)
        staff_user = baker.make("users.User", is_staff=True, is_valid=True)
        baker.make(StructureMember, structure=structure, user=staff_user, is_admin=True)
        data = {
            "first_name": "Foo",
            "last_name": "Bar",
            "email": "foo@bar.com",
            "password": "lkqjfl123!)p",
            "siret": establishment.siret,
        }
        response = self.client.post("/auth/register-structure-and-user/", data)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(StructureMember.objects.get(user__email="foo@bar.com").is_admin)

    def test_register_PE_user_and_struct_without_PE_email(self):
        self.client.force_authenticate(user=None)
        po_agency = baker.make(
            "Structure",
            siret="12345678901234",
            typology=StructureTypology.objects.get(value="PE"),
        )
        establishment = baker.make("Establishment", siret=po_agency.siret)
        data = {
            "first_name": "Foo",
            "last_name": "Bar",
            "email": "foo@bar.com",
            "password": "lkqjfl123!)p",
            "siret": establishment.siret,
        }
        response = self.client.post("/auth/register-structure-and-user/", data)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(email="foo@pole-emploi.fr").exists())

    def test_register_PE_user_and_struct_with_PE_email(self):
        self.client.force_authenticate(user=None)
        po_agency = baker.make(
            "Structure",
            siret="12345678901234",
            typology=StructureTypology.objects.get(value="PE"),
        )
        establishment = baker.make("Establishment", siret=po_agency.siret)
        data = {
            "first_name": "Foo",
            "last_name": "Bar",
            "email": "foo@pole-emploi.fr",
            "password": "lkqjfl123!)p",
            "siret": establishment.siret,
        }
        response = self.client.post("/auth/register-structure-and-user/", data)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(email="foo@pole-emploi.fr").exists())

    def test_register_PE_user_and_struct_with_PE_email_dont_need_admin_validation(self):
        self.client.force_authenticate(user=None)
        po_agency = baker.make(
            "Structure",
            siret="12345678901234",
            typology=StructureTypology.objects.get(value="PE"),
        )
        establishment = baker.make("Establishment", siret=po_agency.siret)
        data = {
            "first_name": "Foo",
            "last_name": "Bar",
            "email": "foo@pole-emploi.fr",
            "password": "lkqjfl123!)p",
            "siret": establishment.siret,
        }
        response = self.client.post("/auth/register-structure-and-user/", data)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(StructureMember.objects.get(user__email="foo@pole-emploi.fr"))
