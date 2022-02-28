import csv
import tempfile
from io import StringIO

from django.core import mail
from django.core.management import call_command
from model_bakery import baker
from rest_framework.test import APITestCase

from dora.rest_auth.models import Token
from dora.structures.models import (
    Structure,
    StructureMember,
    StructurePutativeMember,
    StructureSource,
)
from dora.users.models import User

DUMMY_STRUCTURE = {
    "siret": "12345678901234",
    "typology": "PE",
    "name": "Ma structure",
    "short_desc": "Description courte",
    "postal_code": "75001",
    "city": "Paris",
    "address1": "5, avenue de la République",
}


class StructureTestCase(APITestCase):
    def setUp(self):
        self.me = baker.make("users.User", is_valid=True)
        self.superuser = baker.make("users.User", is_staff=True, is_valid=True)
        self.bizdev = baker.make("users.User", is_bizdev=True, is_valid=True)
        self.my_struct = baker.make("Structure")
        self.my_struct.members.add(self.me)

        self.my_other_struct = baker.make("Structure", creator=None, last_editor=None)
        self.my_other_struct.members.add(self.me)

        self.other_struct = baker.make("Structure")
        self.client.force_authenticate(user=self.me)

    # Visibility

    def test_can_see_my_struct(self):
        response = self.client.get("/structures/")
        structures_ids = [s["slug"] for s in response.data]
        self.assertIn(self.my_struct.slug, structures_ids)
        self.assertIn(self.my_other_struct.slug, structures_ids)

    def test_can_see_others_struct(self):
        response = self.client.get("/structures/")
        structures_ids = [s["slug"] for s in response.data]
        self.assertIn(self.other_struct.slug, structures_ids)

    # Modification

    def test_can_edit_my_structures(self):
        response = self.client.patch(
            f"/structures/{self.my_struct.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/structures/{self.my_struct.slug}/")
        self.assertEqual(response.data["name"], "xxx")

    def test_cant_edit_others_structures(self):
        response = self.client.patch(
            f"/structures/{self.other_struct.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 403)

    def test_edit_structures_updates_last_editor(self):
        response = self.client.patch(
            f"/structures/{self.my_other_struct.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 200)
        slug = response.data["slug"]
        s = Structure.objects.get(slug=slug)
        self.assertEqual(s.last_editor, self.me)

    def test_can_write_field_true(self):
        response = self.client.get(f"/structures/{self.my_struct.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["can_write"], True)

    def test_can_write_field_false(self):
        response = self.client.get(f"/structures/{self.other_struct.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["can_write"], False)

    # Superuser

    def test_superuser_can_sees_everything(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get("/structures/")
        services_ids = [s["slug"] for s in response.data]
        self.assertIn(self.my_struct.slug, services_ids)
        self.assertIn(self.my_other_struct.slug, services_ids)
        self.assertIn(self.other_struct.slug, services_ids)

    def test_superuser_can_edit_everything(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.patch(
            f"/structures/{self.my_struct.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/structures/{self.my_struct.slug}/")
        self.assertEqual(response.data["name"], "xxx")

    def test_superuser_can_write_field_true(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(f"/structures/{self.my_struct.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["can_write"], True)

    def test_bizdev_cant_edit_everything(self):
        self.client.force_authenticate(user=self.bizdev)
        response = self.client.patch(
            f"/structures/{self.my_struct.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 403)

    def test_bizdev_write_field_false(self):
        self.client.force_authenticate(user=self.bizdev)
        response = self.client.get(f"/structures/{self.my_struct.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["can_write"], False)

    # Adding

    def test_can_add_structure(self):
        response = self.client.post(
            "/structures/",
            DUMMY_STRUCTURE,
        )
        self.assertEqual(response.status_code, 201)
        slug = response.data["slug"]
        Structure.objects.get(slug=slug)

    def test_adding_structure_populates_creator_last_editor(self):
        response = self.client.post(
            "/structures/",
            DUMMY_STRUCTURE,
        )
        self.assertEqual(response.status_code, 201)
        slug = response.data["slug"]
        new_structure = Structure.objects.get(slug=slug)
        self.assertEqual(new_structure.creator, self.me)
        self.assertEqual(new_structure.last_editor, self.me)

    def test_adding_structure_sets_source(self):
        response = self.client.post(
            "/structures/",
            DUMMY_STRUCTURE,
        )
        self.assertEqual(response.status_code, 201)
        slug = response.data["slug"]
        s = Structure.objects.get(slug=slug)
        self.assertEqual(s.source, StructureSource.STRUCT_STAFF)

    def test_adding_structure_by_superuser_sets_source(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            "/structures/",
            DUMMY_STRUCTURE,
        )
        self.assertEqual(response.status_code, 201)
        slug = response.data["slug"]
        s = Structure.objects.get(slug=slug)
        self.assertEqual(s.source, StructureSource.DORA_STAFF)

    # Deleting

    def test_cant_delete_structure(self):
        response = self.client.delete(
            f"/structures/{self.my_struct.slug}/",
        )
        self.assertEqual(response.status_code, 403)

    # get_my_services
    def test_filter_my_services_only(self):
        response = self.client.get("/structures/?mine=1")
        services_ids = [s["slug"] for s in response.data]
        self.assertIn(self.my_struct.slug, services_ids)
        self.assertIn(self.my_other_struct.slug, services_ids)
        self.assertNotIn(self.other_struct.slug, services_ids)


class StructureMemberTestCase(APITestCase):
    def setUp(self):
        self.me = baker.make("users.User", is_valid=True)
        self.user1 = baker.make("users.User", is_valid=True)
        self.user2 = baker.make("users.User", is_valid=True)
        self.my_other_struct_user = baker.make("users.User", is_valid=True)
        self.another_struct_user = baker.make("users.User", is_valid=True)
        self.unaccepted_admin = baker.make("users.User", is_valid=True)
        self.bizdev = baker.make("users.User", is_bizdev=True, is_valid=True)
        self.superuser = baker.make("users.User", is_staff=True, is_valid=True)

        self.my_struct = baker.make("Structure")
        self.my_struct.members.add(
            self.me,
            through_defaults={
                "is_admin": True,
            },
        )

        self.my_struct.members.add(
            self.user1,
            through_defaults={
                "is_admin": True,
            },
        )
        self.my_struct.members.add(
            self.user2,
            through_defaults={
                "is_admin": False,
            },
        )

        self.my_other_struct = baker.make("Structure", creator=None, last_editor=None)
        self.my_other_struct.members.add(
            self.me,
            through_defaults={
                "is_admin": True,
            },
        )
        self.my_other_struct.members.add(self.my_other_struct_user)

        self.other_struct = baker.make("Structure")
        self.other_struct.members.add(
            self.another_struct_user,
            through_defaults={
                "is_admin": True,
            },
        )

    def test_create_struct_creates_member(self):
        # For now, this is only open to staff members
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        member = StructureMember.objects.filter(user=user).first()
        self.assertIsNone(member)
        response = self.client.post(
            "/structures/",
            DUMMY_STRUCTURE,
        )
        self.assertEqual(response.status_code, 201)
        slug = response.data["slug"]
        struct = Structure.objects.get(slug=slug)
        member = StructureMember.objects.filter(user=user).first()
        self.assertIsNotNone(member)
        self.assertEqual(member.structure, struct)
        self.assertTrue(member.is_admin)

    # Visibility lists

    def test_get_request_without_struct_empty(self):
        self.client.force_authenticate(user=self.me)
        response = self.client.get("/structure-members/")
        self.assertEquals(response.data, [])

    def test_admin_user_can_see_structure_members(self):
        self.client.force_authenticate(user=self.me)
        response = self.client.get(
            f"/structure-members/?structure={self.my_struct.slug}"
        )
        self.assertEqual(response.status_code, 200)
        emails = [m["user"]["email"] for m in response.data]
        self.assertIn(self.me.email, emails)
        self.assertIn(self.user1.email, emails)
        self.assertIn(self.user2.email, emails)

    def test_unaccepted_admin_user_cant_see_structure_members(self):
        self.client.force_authenticate(user=self.unaccepted_admin)
        response = self.client.get(
            f"/structure-members/?structure={self.my_struct.slug}"
        )
        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_cant_see_structure_members(self):
        response = self.client.get(
            f"/structure-members/?structure={self.my_struct.slug}"
        )
        self.assertEqual(response.status_code, 403)

    def test_standard_user_cant_see_structure_members(self):
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(
            f"/structure-members/?structure={self.my_struct.slug}"
        )
        self.assertEqual(response.status_code, 403)

    def test_super_user_can_see_structure_members(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            f"/structure-members/?structure={self.my_struct.slug}"
        )
        self.assertEqual(response.status_code, 200)
        emails = [m["user"]["email"] for m in response.data]
        self.assertIn(self.me.email, emails)
        self.assertIn(self.user1.email, emails)
        self.assertIn(self.user2.email, emails)

    def test_bizdev_can_see_structure_members(self):
        self.client.force_authenticate(user=self.bizdev)
        response = self.client.get(
            f"/structure-members/?structure={self.my_struct.slug}"
        )
        self.assertEqual(response.status_code, 200)
        emails = [m["user"]["email"] for m in response.data]
        self.assertIn(self.me.email, emails)
        self.assertIn(self.user1.email, emails)
        self.assertIn(self.user2.email, emails)

    # Visibility instance

    def test_admin_user_can_see_structure_member(self):
        self.client.force_authenticate(user=self.me)
        member = self.user1.membership.get(structure=self.my_struct)
        response = self.client.get(f"/structure-members/{member.id}/")
        self.assertEqual(response.status_code, 200)

    def test_unaccepted_admin_user_cant_see_structure_member(self):
        self.client.force_authenticate(user=self.unaccepted_admin)
        member = self.user1.membership.get(structure=self.my_struct)
        response = self.client.get(f"/structure-members/{member.id}/")
        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_cant_see_structure_member(self):
        member = self.user1.membership.get(structure=self.my_struct)
        response = self.client.get(f"/structure-members/{member.id}/")
        self.assertEqual(response.status_code, 404)

    def test_standard_user_cant_see_structure_member(self):
        self.client.force_authenticate(user=self.user2)
        member = self.user1.membership.get(structure=self.my_struct)
        response = self.client.get(f"/structure-members/{member.id}/")
        self.assertEqual(response.status_code, 404)

    def test_super_user_can_see_structure_member(self):
        self.client.force_authenticate(user=self.superuser)
        member = self.user1.membership.get(structure=self.my_struct)
        response = self.client.get(f"/structure-members/{member.id}/")
        self.assertEqual(response.status_code, 200)

    def test_bizdev_can_see_structure_member(self):
        self.client.force_authenticate(user=self.bizdev)
        member = self.user1.membership.get(structure=self.my_struct)
        response = self.client.get(f"/structure-members/{member.id}/")
        self.assertEqual(response.status_code, 200)

    # Edition

    def test_admin_user_can_change_structure_members(self):
        self.client.force_authenticate(user=self.me)
        member = self.user1.membership.get(structure=self.my_struct)
        self.assertTrue(member.is_admin)
        response = self.client.patch(
            f"/structure-members/{member.id}/",
            {"is_admin": False},
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/structure-members/{member.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["is_admin"], False)

    def test_unaccepted_admin_user_cant_change_structure_members(self):
        self.client.force_authenticate(user=self.unaccepted_admin)
        member = self.user1.membership.get(structure=self.my_struct)
        self.assertTrue(member.is_admin)
        response = self.client.patch(
            f"/structure-members/{member.id}/",
            {"is_admin": False},
        )
        self.assertEqual(response.status_code, 404)

    def test_cant_change_email(self):
        self.client.force_authenticate(user=self.me)
        member = self.user1.membership.get(structure=self.my_struct)
        response = self.client.patch(
            f"/structure-members/{member.id}/",
            {"user": {"email": "FOO@BAR.BUZ"}},
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/structure-members/{member.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.data["user"]["email"], "FOO@BAR.BUZ")

    def test_cant_change_name(self):
        self.client.force_authenticate(user=self.me)
        member = self.user1.membership.get(structure=self.my_struct)
        response = self.client.patch(
            f"/structure-members/{member.id}/",
            {"user": {"last_name": "FOO", "first_name": "FIZ"}},
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/structure-members/{member.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.data["user"]["last_name"], "FOO")
        self.assertNotEqual(response.data["user"]["first_name"], "FIZ")

    def test_anonymous_user_cant_change_structure_members(self):
        member = self.user1.membership.get(structure=self.my_struct)
        response = self.client.patch(
            f"/structure-members/{member.id}/",
            {"is_admin": False, "user": {"last_name": "FOO", "email": "FOO@BAR.BUZ"}},
        )
        self.assertEqual(response.status_code, 404)

    def test_standard_user_cant_change_structure_members(self):
        self.client.force_authenticate(user=self.user2)
        member = self.user1.membership.get(structure=self.my_struct)
        response = self.client.patch(
            f"/structure-members/{member.id}/",
            {"is_admin": False, "user": {"last_name": "FOO", "email": "FOO@BAR.BUZ"}},
        )
        self.assertEqual(response.status_code, 404)

    def test_standard_user_cant_gain_admin_privilege(self):
        self.client.force_authenticate(user=self.user2)
        member = self.user2.membership.get(structure=self.my_struct)
        self.assertFalse(member.is_admin)
        response = self.client.patch(
            f"/structure-members/{member.id}/",
            {"is_admin": True},
        )
        self.assertEqual(response.status_code, 404)

    def test_super_user_can_change_structure_members(self):
        self.client.force_authenticate(user=self.superuser)
        member = self.user1.membership.get(structure=self.my_struct)
        response = self.client.patch(
            f"/structure-members/{member.id}/",
            {"is_admin": False, "user": {"last_name": "FOO", "email": "FOO@BAR.BUZ"}},
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/structure-members/{member.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["is_admin"], False)
        self.assertNotEqual(response.data["user"]["last_name"], "FOO")
        self.assertNotEqual(response.data["user"]["email"], "FOO@BAR.BUZ")

    def test_bizdev_user_cant_change_structure_members(self):
        self.client.force_authenticate(user=self.bizdev)
        member = self.user1.membership.get(structure=self.my_struct)
        self.assertTrue(member.is_admin)
        response = self.client.patch(
            f"/structure-members/{member.id}/",
            {"is_admin": False, "user": {"last_name": "FOO", "email": "FOO@BAR.BUZ"}},
        )
        self.assertEqual(response.status_code, 403)

    # Deletion

    def test_admin_user_can_delete_structure_members(self):
        self.client.force_authenticate(user=self.me)
        member = self.user1.membership.get(structure=self.my_struct)
        response = self.client.delete(
            f"/structure-members/{member.id}/",
        )
        self.assertEqual(response.status_code, 204)
        response = self.client.get(f"/structure-members/{member.id}/")
        self.assertEqual(response.status_code, 404)

    def test_unaccepted_admin_user_cant_delete_structure_members(self):
        self.client.force_authenticate(user=self.unaccepted_admin)
        member = self.user1.membership.get(structure=self.my_struct)
        response = self.client.delete(
            f"/structure-members/{member.id}/",
        )
        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_cant_delete_structure_members(self):
        member = self.user1.membership.get(structure=self.my_struct)
        response = self.client.delete(
            f"/structure-members/{member.id}/",
        )
        self.assertEqual(response.status_code, 404)

    def test_standard_user_cant_delete_structure_members(self):
        self.client.force_authenticate(user=self.user2)
        member = self.user1.membership.get(structure=self.my_struct)
        response = self.client.delete(
            f"/structure-members/{member.id}/",
        )
        self.assertEqual(response.status_code, 404)

    def test_super_user_can_delete_structure_members(self):
        self.client.force_authenticate(user=self.superuser)
        member = self.user1.membership.get(structure=self.my_struct)
        response = self.client.delete(
            f"/structure-members/{member.id}/",
        )
        self.assertEqual(response.status_code, 204)
        response = self.client.get(f"/structure-members/{member.id}/")
        self.assertEqual(response.status_code, 404)

    def test_bizdev_user_cant_delete_structure_members(self):
        self.client.force_authenticate(user=self.bizdev)
        member = self.user1.membership.get(structure=self.my_struct)
        response = self.client.delete(
            f"/structure-members/{member.id}/",
        )
        self.assertEqual(response.status_code, 403)

    # Creation
    def test_post_request_without_struct_empty(self):
        self.client.force_authenticate(user=self.me)
        response = self.client.post(
            "/structure-members/",
            {"user": {"last_name": "FOO", "email": "FOO@BAR.BUZ"}},
        )
        self.assertEquals(response.status_code, 403)

    def test_admin_user_can_invite_new_user(self):
        self.client.force_authenticate(user=self.me)

        response = self.client.post(
            f"/structure-putative-members/?structure={self.my_struct.slug}",
            {
                "is_admin": False,
                "user": {
                    "last_name": "FOO",
                    "first_name": "FIZZ",
                    "email": "FOO@BAR.BUZ",
                },
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["is_admin"], False)
        self.assertEqual(response.data["user"]["first_name"], "FIZZ")
        self.assertEqual(response.data["user"]["last_name"], "FOO")
        self.assertEqual(response.data["user"]["email"], "FOO@BAR.BUZ")

    def test_unaccepted_admin_user_cant_invite_new_user(self):
        self.client.force_authenticate(user=self.unaccepted_admin)

        response = self.client.post(
            f"/structure-putative-members/?structure={self.my_struct.slug}",
            {
                "is_admin": False,
                "user": {
                    "last_name": "FOO",
                    "first_name": "FIZZ",
                    "email": "FOO@BAR.BUZ",
                },
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            StructurePutativeMember.objects.filter(
                structure=self.my_struct, user__email="FOO@BAR.BUZ"
            ).exists()
        )

    def test_admin_user_cant_force_validation(self):
        self.client.force_authenticate(user=self.me)

        response = self.client.post(
            f"/structure-putative-members/?structure={self.my_struct.slug}",
            {
                "is_admin": False,
                "user": {"last_name": "FOO", "email": "FOO@BAR.BUZ"},
            },
        )
        self.assertEqual(response.status_code, 201)
        member = response.data["id"]
        response = self.client.get(f"/structure-members/{member}/")
        self.assertEqual(response.status_code, 404)

    def test_admin_user_can_invite_existing_user(self):
        self.client.force_authenticate(user=self.me)

        response = self.client.post(
            f"/structure-putative-members/?structure={self.my_struct.slug}",
            {
                "is_admin": False,
                "user": {
                    "last_name": "FOO",
                    "email": f"{self.another_struct_user.email}",
                },
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["is_admin"], False)
        self.assertNotEqual(response.data["user"]["last_name"], "FOO")
        self.assertEqual(response.data["user"]["email"], self.another_struct_user.email)
        self.assertEqual(len(mail.outbox), 1)

    def test_unaccepted_admin_user_cant_invite_existing_user(self):
        self.client.force_authenticate(user=self.unaccepted_admin)

        response = self.client.post(
            f"/structure-members/?structure={self.my_struct.slug}",
            {
                "is_admin": False,
                "user": {
                    "last_name": "FOO",
                    "email": f"{self.another_struct_user.email}",
                },
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            StructureMember.objects.filter(
                structure=self.my_struct, user__email="FOO@BAR.BUZ"
            ).exists()
        )

    def test_admin_user_cannot_reinvite_valid_member(self):
        self.client.force_authenticate(user=self.me)
        response = self.client.post(
            f"/structure-members/?structure={self.my_struct.slug}",
            {
                "is_admin": False,
                "user": {
                    "last_name": "FOO",
                    "email": f"{self.user2.email}",
                },
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_cant_invite_structure_members(self):
        response = self.client.post(
            f"/structure-members/?structure={self.my_struct.slug}",
            {
                "is_admin": False,
                "user": {
                    "last_name": "FOO",
                    "email": f"{self.another_struct_user.email}",
                },
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_standard_user_cant_invite_structure_members(self):
        self.client.force_authenticate(user=self.user2)
        response = self.client.post(
            f"/structure-members/?structure={self.my_struct.slug}",
            {
                "is_admin": False,
                "user": {
                    "last_name": "FOO",
                    "email": f"{self.another_struct_user.email}",
                },
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_super_user_can_invite_structure_members(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            f"/structure-putative-members/?structure={self.my_struct.slug}",
            {
                "is_admin": False,
                "user": {
                    "last_name": "FOO",
                    "email": f"{self.another_struct_user.email}",
                },
            },
        )
        self.assertEqual(response.status_code, 201)
        member = response.data["id"]
        response = self.client.get(f"/structure-putative-members/{member}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["is_admin"], False)
        self.assertNotEqual(response.data["user"]["last_name"], "FOO")
        self.assertEqual(response.data["user"]["email"], self.another_struct_user.email)
        self.assertEqual(len(mail.outbox), 1)

    def test_bizdev_cant_invite_structure_members(self):
        self.client.force_authenticate(user=self.bizdev)
        response = self.client.post(
            f"/structure-putative-members/?structure={self.my_struct.slug}",
            {
                "is_admin": False,
                "user": {
                    "last_name": "FOO",
                    "email": f"{self.another_struct_user.email}",
                },
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_reinvite_user(self):
        self.client.force_authenticate(user=self.me)
        user = baker.make("users.User", is_valid=True)
        pm = StructurePutativeMember.objects.create(
            user=user, structure=self.my_struct, invited_by_admin=True
        )
        response = self.client.post(
            f"/structure-putative-members/{pm.id}/resend-invite/",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Votre invitation sur DORA", mail.outbox[0].subject)

    def test_admin_cant_reinvite_valid_member(self):
        self.client.force_authenticate(user=self.me)
        user = baker.make("users.User", is_valid=True)
        self.my_struct.members.add(
            user,
        )
        member = user.membership.get(structure=self.my_struct)

        response = self.client.post(
            f"/structure-members/{member.id}/resend-invite/",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(mail.outbox), 0)
        response = self.client.post(
            f"/structure-putative-members/{member.id}/resend-invite/",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(mail.outbox), 0)

    def test_admin_can_reinvite_valid_user_with_no_pw_set(self):
        self.client.force_authenticate(user=self.me)
        user = baker.make("users.User", is_valid=True)
        user.set_unusable_password()
        user.save()
        pm = StructurePutativeMember.objects.create(
            user=user, structure=self.my_struct, invited_by_admin=True
        )
        response = self.client.post(
            f"/structure-putative-members/{pm.id}/resend-invite/",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Votre invitation sur DORA", mail.outbox[0].subject)

    def test_admin_cant_reinvite_user_to_other_struct(self):
        self.client.force_authenticate(user=self.me)
        user = baker.make("users.User", is_valid=True)
        pm = StructurePutativeMember.objects.create(
            user=user, structure=self.other_struct, invited_by_admin=True
        )
        response = self.client.post(
            f"/structure-putative-members/{pm.id}/resend-invite/",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(mail.outbox), 0)

    def test_anonymous_cant_reinvite_user(self):
        user = baker.make("users.User", is_valid=True)
        pm = StructurePutativeMember.objects.create(
            user=user, structure=self.my_struct, invited_by_admin=True
        )
        response = self.client.post(
            f"/structure-putative-members/{pm.id}/resend-invite/",
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(len(mail.outbox), 0)

    def test_standard_user_cant_reinvite_user(self):
        self.client.force_authenticate(user=self.user2)
        user = baker.make("users.User", is_valid=True)
        pm = StructurePutativeMember.objects.create(
            user=user, structure=self.my_struct, invited_by_admin=True
        )
        response = self.client.post(
            f"/structure-putative-members/{pm.id}/resend-invite/",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(mail.outbox), 0)

    def test_superuser_can_reinvite_user(self):
        self.client.force_authenticate(user=self.superuser)
        user = baker.make("users.User", is_valid=True)
        pm = StructurePutativeMember.objects.create(
            user=user, structure=self.my_struct, invited_by_admin=True
        )
        response = self.client.post(
            f"/structure-putative-members/{pm.id}/resend-invite/",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Votre invitation sur DORA", mail.outbox[0].subject)

    def test_bizdev_cant_reinvite_user(self):
        self.client.force_authenticate(user=self.bizdev)
        user = baker.make("users.User", is_valid=True)
        pm = StructurePutativeMember.objects.create(
            user=user, structure=self.my_struct, invited_by_admin=True
        )
        response = self.client.post(
            f"/structure-putative-members/{pm.id}/resend-invite/",
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_user_can_remove_its_admin_privilege(self):
        self.client.force_authenticate(user=self.me)
        member = self.me.membership.get(structure=self.my_struct)
        self.assertTrue(member.is_admin)
        response = self.client.patch(
            f"/structure-members/{member.id}/",
            {"is_admin": False},
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/structure-members/{member.id}/")
        self.assertEqual(response.status_code, 404)

    # Invitation acceptation
    def test_user_can_accept_invitation(self):
        admin = baker.make("users.User", is_valid=True)
        structure = baker.make("Structure")
        structure.members.add(
            admin,
            through_defaults={
                "is_admin": True,
            },
        ),
        self.client.force_authenticate(user=admin)
        response = self.client.post(
            f"/structure-putative-members/?structure={structure.slug}",
            {
                "is_admin": False,
                "user": {
                    "last_name": "FOO",
                    "first_name": "FIZZ",
                    "email": "FOO@BAR.BUZ",
                },
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        self.client.force_authenticate(user=None)

        member = StructurePutativeMember.objects.get(pk=response.data["id"])

        invit_key = Token.objects.get(user=member.user)
        self.assertIn(invit_key.key, mail.outbox[0].body)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {invit_key.key}")
        response = self.client.post(
            f"/structure-putative-members/{member.id}/accept-invite/",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["must_set_password"])
        token = response.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        response = self.client.post(
            "/auth/password/reset/confirm/",
            {"new_password": "aoinf156azfeAF&é"},
            headers={"Authorization": f"Token {token}"},
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Token.objects.filter(user=member.user).count(), 0)
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn("Invitation acceptée", mail.outbox[1].subject)
        self.assertIn("FOO", mail.outbox[1].body)
        self.assertIn("FIZZ", mail.outbox[1].body)
        self.assertIn("FOO@BAR.BUZ", mail.outbox[1].body)
        self.assertIn(structure.name, mail.outbox[1].body)

        member = StructureMember.objects.get(
            user=member.user, structure=member.structure
        )
        self.assertTrue(member.user.is_valid)

    def test_user_must_set_strong_pw(self):
        self.client.force_authenticate(user=self.me)
        response = self.client.post(
            f"/structure-putative-members/?structure={self.my_struct.slug}",
            {
                "is_admin": False,
                "user": {
                    "last_name": "FOO",
                    "first_name": "FIZZ",
                    "email": "FOO@BAR.BUZ",
                },
            },
        )
        self.assertEqual(response.status_code, 201)
        member = StructurePutativeMember.objects.get(pk=response.data["id"])
        self.client.force_authenticate(user=member.user)

        response = self.client.post(
            "/auth/password/reset/confirm/", {"new_password": "ABBA"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["non_field_errors"][0]["code"], "password_too_short"
        )

    # Fail safes
    def test_super_user_can_remove_last_admin(self):
        self.client.force_authenticate(user=self.superuser)
        member = self.me.membership.get(structure=self.my_other_struct)
        self.assertTrue(member.is_admin)
        response = self.client.patch(
            f"/structure-members/{member.id}/",
            {"is_admin": False},
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/structure-members/{member.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["is_admin"], False)

    def test_admin_user_cant_remove_its_admin_privilege_if_last_admin(self):
        self.client.force_authenticate(user=self.me)
        member = self.me.membership.get(structure=self.my_other_struct)
        self.assertTrue(member.is_admin)
        response = self.client.patch(
            f"/structure-members/{member.id}/",
            {"is_admin": False},
        )
        self.assertEqual(response.status_code, 403)
        response = self.client.get(f"/structure-members/{member.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["is_admin"], True)


class MassInviteTestCase(APITestCase):
    def setUp(self):
        self.tmp_file = tempfile.NamedTemporaryFile(mode="w", newline="")
        self.csv_writer = self.create_csv(self.tmp_file)
        self.inviter_name = "Mr. Inviter"

    def create_csv(self, file):
        writer = csv.writer(file, delimiter=",")
        writer.writerow(
            ["lastname", "firstname", "email", "siret", "code_insee", "admin"]
        )
        return writer

    def create_structure(self, **kwargs):
        return baker.make("Structure", **kwargs)

    def add_row(self, row):
        self.csv_writer.writerow(row)

    def call_command(self):
        self.tmp_file.seek(0)
        out = StringIO()
        err = StringIO()
        call_command(
            "mass_invite", self.tmp_file.name, self.inviter_name, stdout=out, stderr=err
        )
        self.tmp_file.seek(0)
        return out.getvalue(), err.getvalue()

    ########

    def test_wrong_siret_wont_create_anything(self):
        self.add_row(["foo", "buzz", "foo@buzz.com", "12345678901234", "", "FALSE"])
        out, err = self.call_command()
        self.assertIn("Structure 12345678901234 doesn't exist", err)
        self.assertFalse(Structure.objects.filter(siret="12345").exists())
        self.assertFalse(User.objects.filter(email="foo@buzz.com").exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_siret_wont_create_anything(self):
        self.add_row(["foo", "buzz", "foo@buzz.com", "1234", "", "FALSE"])
        out, err = self.call_command()
        self.assertIn("code_structure", err)
        self.assertIn(
            "Assurez-vous que ce champ comporte au moins 5\\xa0caractères.", err
        )
        self.assertFalse(Structure.objects.filter(siret="12345").exists())
        self.assertFalse(User.objects.filter(email="foo@buzz.com").exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_wrong_city_code_wont_create_anything(self):
        structure = self.create_structure()
        self.add_row(["foo", "buzz", "foo@buzz.com", structure.siret, "00000", "FALSE"])
        out, err = self.call_command()
        self.assertIn("Invalid insee code 00000", err)
        self.assertFalse(User.objects.filter(email="foo@buzz.com").exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_can_invite_new_user(self):
        structure = self.create_structure()
        self.add_row(["Foo", "Buzz", "foo@buzz.com", structure.siret, "", "FALSE"])
        out, err = self.call_command()
        user = User.objects.filter(email="foo@buzz.com").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.get_full_name(), "Buzz Foo")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "[DORA] Votre invitation sur DORA")
        self.assertIn(
            "Buzz",
            mail.outbox[0].body,
        )
        self.assertIn(
            f"{ self.inviter_name } vous a invité(e) à rejoindre la structure { structure.name }",
            mail.outbox[0].body,
        )

    def test_new_users_are_automatically_accepted(self):
        structure = self.create_structure()
        self.add_row(["Foo", "Buzz", "foo@buzz.com", structure.siret, "", "FALSE"])
        out, err = self.call_command()
        self.assertTrue(
            StructurePutativeMember.objects.filter(
                user__email="foo@buzz.com", invited_by_admin=True
            ).exists()
        )

    def test_can_invite_new_user_with_safir(self):
        structure = self.create_structure(code_safir_pe="98765")
        self.add_row(
            ["Foo", "Buzz", "foo@buzz.com", structure.code_safir_pe, "", "FALSE"]
        )
        out, err = self.call_command()
        user = User.objects.filter(email="foo@buzz.com").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.get_full_name(), "Buzz Foo")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "[DORA] Votre invitation sur DORA")
        self.assertIn(
            "Buzz",
            mail.outbox[0].body,
        )
        self.assertIn(
            f"{ self.inviter_name } vous a invité(e) à rejoindre la structure { structure.name }",
            mail.outbox[0].body,
        )

    def test_idempotent(self):
        structure = self.create_structure()
        self.add_row(["Foo", "Buzz", "foo@buzz.com", structure.siret, "", "FALSE"])
        out1, err1 = self.call_command()
        out2, err2 = self.call_command()
        self.assertIn("Member foo@buzz.com already invited", out2)
        self.assertEquals(Structure.objects.filter(siret=structure.siret).count(), 1)
        self.assertEquals(User.objects.filter(email="foo@buzz.com").count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_can_invite_as_non_admin(self):
        structure = self.create_structure()
        self.add_row(["Foo", "Buzz", "foo@buzz.com", structure.siret, "", "FALSE"])
        out, err = self.call_command()
        members = StructurePutativeMember.objects.filter(
            user__email="foo@buzz.com", structure=structure
        )
        self.assertEqual(members.count(), 1)
        self.assertFalse(members[0].is_admin)

    def test_can_invite_as_admin(self):
        structure = self.create_structure()
        self.add_row(["Foo", "Buzz", "foo@buzz.com", structure.siret, "", "TRUE"])
        out, err = self.call_command()
        members = StructurePutativeMember.objects.filter(
            user__email="foo@buzz.com", structure=structure, invited_by_admin=True
        )
        self.assertEqual(members.count(), 1)
        self.assertTrue(members[0].is_admin)

    def test_admin_is_TRUE_or_FALSE(self):
        structure = self.create_structure()
        self.add_row(["Foo", "Buzz", "foo@buzz.com", structure.siret, "", "XXX"])
        out, err = self.call_command()
        self.assertIn("is_admin", err)
        self.assertIn("«\\xa0XXX\\xa0» n'est pas un choix valide.", err)
        self.assertEquals(User.objects.filter(email="foo@buzz.com").count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_is_valid(self):
        structure = self.create_structure()
        self.add_row(["Foo", "Buzz", "foo.buzz.com", structure.siret, "", "FALSE"])
        out, err = self.call_command()
        self.assertIn("email", err)
        self.assertIn("Saisissez une adresse e-mail valide.", err)
        self.assertEquals(User.objects.filter(email="foo.buzz.com").count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_firstname_is_valid(self):
        structure = self.create_structure()
        self.add_row(["Foo", "", "foo@buzz.com", structure.siret, "", "FALSE"])
        out, err = self.call_command()
        self.assertIn("first_name", err)
        self.assertIn("Ce champ ne peut être vide.", err)
        self.assertEquals(User.objects.filter(email="foo@buzz.com").count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_lastname_is_valid(self):
        structure = self.create_structure()
        self.add_row(["", "Buzz", "foo@buzz.com", structure.siret, "", "FALSE"])
        out, err = self.call_command()
        self.assertIn("last_name", err)
        self.assertIn("Ce champ ne peut être vide.", err)
        self.assertEquals(User.objects.filter(email="foo@buzz.com").count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_invitee_not_a_valid_user_yet(self):
        structure = self.create_structure()
        self.add_row(["Foo", "Buzz", "foo@buzz.com", structure.siret, "", "FALSE"])
        out, err = self.call_command()
        user = User.objects.filter(email="foo@buzz.com").first()
        self.assertFalse(user.is_valid)

    def test_invitee_not_a_valid_member_yet(self):
        structure = self.create_structure()
        self.add_row(["Foo", "Buzz", "foo@buzz.com", structure.siret, "", "FALSE"])
        out, err = self.call_command()
        members = StructurePutativeMember.objects.filter(
            user__email="foo@buzz.com", structure=structure
        )
        self.assertTrue(members.exists())
        real_members = StructureMember.objects.filter(
            user__email="foo@buzz.com", structure=structure
        )
        self.assertFalse(real_members.exists())

    def test_can_invite_existing_user(self):
        structure = self.create_structure()
        user = baker.make(
            "users.User", first_name="foo", last_name="bar", is_valid=True
        )
        self.add_row(
            [user.last_name, user.first_name, user.email, structure.siret, "", "FALSE"]
        )
        out, err = self.call_command()
        self.assertEqual(User.objects.filter(email=user.email).count(), 1)
        fresh_user = User.objects.filter(email=user.email).first()
        self.assertEqual(fresh_user.get_full_name(), user.get_full_name())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "[DORA] Votre invitation sur DORA")
        self.assertIn(
            fresh_user.get_short_name(),
            mail.outbox[0].body,
        )
        self.assertEqual(
            StructurePutativeMember.objects.filter(
                user=user, structure=structure
            ).count(),
            1,
        )

    def test_wont_rename_existing_user(self):
        structure = self.create_structure()
        user = baker.make("users.User", is_valid=True)
        self.add_row(
            ["NEWNAME", "NEWFIRSTNAME", user.email, structure.siret, "", "FALSE"]
        )
        out, err = self.call_command()
        fresh_user = User.objects.filter(email=user.email).first()
        self.assertEqual(fresh_user.get_full_name(), user.get_full_name())

    def test_existing_user_stay_valid_user(self):
        structure = self.create_structure()
        user = baker.make(
            "users.User", first_name="foo", last_name="bar", is_valid=True
        )
        self.add_row(
            [user.last_name, user.first_name, user.email, structure.siret, "", "FALSE"]
        )
        out, err = self.call_command()
        fresh_user = User.objects.filter(email=user.email).first()
        self.assertTrue(fresh_user.is_valid)

    def test_existing_user_stay_valid_member(self):
        structure = self.create_structure()
        user = baker.make(
            "users.User", first_name="foo", last_name="bar", is_valid=True
        )
        StructureMember.objects.create(
            structure=structure,
            user=user,
        )
        self.add_row(
            [user.last_name, user.first_name, user.email, structure.siret, "", "FALSE"]
        )
        out, err = self.call_command()
        fresh_member = StructureMember.objects.get(user=user, structure=structure)
        self.assertFalse(fresh_member.is_admin)

    def test_member_can_be_promoted_to_admin(self):
        structure = self.create_structure()
        user = baker.make(
            "users.User", first_name="foo", last_name="bar", is_valid=True
        )
        StructureMember.objects.create(structure=structure, user=user, is_admin=False)
        self.add_row(
            [user.last_name, user.first_name, user.email, structure.siret, "", "TRUE"]
        )
        out, err = self.call_command()
        fresh_member = StructureMember.objects.get(user=user, structure=structure)
        self.assertTrue(fresh_member.is_admin)

    def test_member_cant_be_demoted_from_admin(self):
        structure = self.create_structure()
        user = baker.make(
            "users.User", first_name="foo", last_name="bar", is_valid=True
        )
        StructureMember.objects.create(structure=structure, user=user, is_admin=True)
        self.add_row(
            [user.last_name, user.first_name, user.email, structure.siret, "", "FALSE"]
        )
        out, err = self.call_command()
        fresh_member = StructureMember.objects.get(user=user, structure=structure)
        self.assertTrue(fresh_member.is_admin)

    def test_create_new_antenna_on_the_fly(self):
        structure = self.create_structure(name="My Structure")
        city = baker.make("City", code="93048", name="Montreuil")
        self.add_row(
            ["Foo", "Buzz", "foo@buzz.com", structure.siret, city.code, "FALSE"]
        )
        out, err = self.call_command()
        antennas = Structure.objects.filter(parent=structure)
        self.assertEqual(antennas.count(), 1)
        antenna = antennas[0]
        self.assertEqual(antenna.name, "My Structure – Montreuil")
        self.assertEqual(antenna.ape, structure.ape)
        self.assertEqual(antenna.siret, f"{structure.siret[:9]}{city.code}")
        self.assertEqual(antenna.city, city.name)
        self.assertEqual(antenna.typology, structure.typology)
        self.assertEqual(antenna.short_desc, structure.short_desc)
        self.assertEqual(antenna.full_desc, structure.full_desc)
        self.assertEqual(antenna.creator, User.objects.get_dora_bot())
        self.assertEqual(antenna.source, StructureSource.BATCH_INVITE)
        self.assertEqual(antenna.parent, structure)
        self.assertTrue(antenna.is_antenna)

        user = User.objects.filter(email="foo@buzz.com").first()
        self.assertIsNotNone(user)
        self.assertEqual(len(mail.outbox), 1)

    def test_user_belong_to_antenna(self):
        structure = self.create_structure(name="My Structure")
        city = baker.make("City", code="93048", name="Montreuil")
        self.add_row(
            ["Foo", "Buzz", "foo@buzz.com", structure.siret, city.code, "FALSE"]
        )
        out, err = self.call_command()
        antenna = Structure.objects.filter(parent=structure).first()
        self.assertEqual(
            StructurePutativeMember.objects.filter(
                structure=antenna, user__email="foo@buzz.com"
            ).count(),
            1,
        )
        self.assertIn(
            f"{ self.inviter_name } vous a invité(e) à rejoindre la structure { antenna.name }",
            mail.outbox[0].body,
        )

    def test_user_dont_belong_to_parent(self):
        structure = self.create_structure(name="My Structure")
        city = baker.make("City", code="93048", name="Montreuil")
        self.add_row(
            ["Foo", "Buzz", "foo@buzz.com", structure.siret, city.code, "FALSE"]
        )
        out, err = self.call_command()
        self.assertEqual(
            StructureMember.objects.filter(
                structure=structure, user__email="foo@buzz.com"
            ).count(),
            0,
        )

    def test_find_existing_antenna(self):
        structure = self.create_structure(name="My Structure", siret="12345678901234")
        antenna = baker.make(
            "Structure", siret="12345678993048", is_antenna=True, parent=structure
        )
        city = baker.make("City", code="93048", name="Montreuil")
        self.add_row(
            ["Foo", "Buzz", "foo@buzz.com", structure.siret, city.code, "FALSE"]
        )
        out, err = self.call_command()
        antennas = Structure.objects.filter(parent=structure)
        self.assertEqual(antennas.count(), 1)
        antenna = antennas[0]
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            StructurePutativeMember.objects.filter(
                structure=antenna, user__email="foo@buzz.com"
            ).count(),
            1,
        )
        self.assertIn(
            f"{ self.inviter_name } vous a invité(e) à rejoindre la structure { antenna.name }",
            mail.outbox[0].body,
        )
