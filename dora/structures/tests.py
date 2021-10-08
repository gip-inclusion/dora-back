from django.core import mail
from model_bakery import baker
from rest_framework.test import APITestCase

from dora.structures.models import Structure, StructureSource

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
        self.me = baker.make("users.User")
        self.superuser = baker.make("users.User", is_staff=True)
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

    def test_adding_structure_by_admin_sets_source(self):
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

    # Test structure creation/joining; maybe in rest_auth app?
    # Need to mock email sending
    # def test_adding_structure_creates_membership(self):
    #     self.assertTrue(False)

    # def test_adding_structure_makes_admin(self):
    #     self.assertTrue(False)

    # def test_join_structure_makes_nonadmin(self):
    #     self.assertTrue(False)


class StructureMemberTestCase(APITestCase):
    def setUp(self):
        self.me = baker.make("users.User")
        self.user1 = baker.make("users.User")
        self.user2 = baker.make("users.User")
        self.my_other_struct_user = baker.make("users.User")
        self.another_struct_user = baker.make("users.User")

        self.superuser = baker.make("users.User", is_staff=True)

        self.my_struct = baker.make("Structure")
        self.my_struct.members.add(self.me, through_defaults={"is_admin": True}),
        self.my_struct.members.add(self.user1, through_defaults={"is_admin": True})
        self.my_struct.members.add(self.user2, through_defaults={"is_admin": False})

        self.my_other_struct = baker.make("Structure", creator=None, last_editor=None)
        self.my_other_struct.members.add(self.me, through_defaults={"is_admin": True})
        self.my_other_struct.members.add(self.my_other_struct_user)

        self.other_struct = baker.make("Structure")
        self.other_struct.members.add(
            self.another_struct_user, through_defaults={"is_admin": True}
        )

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

    # Visibility instance

    def test_admin_user_can_see_structure_member(self):
        self.client.force_authenticate(user=self.me)
        member = self.user1.membership.get(structure=self.my_struct)
        response = self.client.get(f"/structure-members/{member.id}/")
        self.assertEqual(response.status_code, 200)

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
            {"user": {"name": "FOO"}},
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/structure-members/{member.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.data["user"]["name"], "FOO")

    def test_anonymous_user_cant_change_structure_members(self):
        member = self.user1.membership.get(structure=self.my_struct)
        response = self.client.patch(
            f"/structure-members/{member.id}/",
            {"is_admin": False, "user": {"name": "FOO", "email": "FOO@BAR.BUZ"}},
        )
        self.assertEqual(response.status_code, 404)

    def test_standard_user_cant_change_structure_members(self):
        self.client.force_authenticate(user=self.user2)
        member = self.user1.membership.get(structure=self.my_struct)
        response = self.client.patch(
            f"/structure-members/{member.id}/",
            {"is_admin": False, "user": {"name": "FOO", "email": "FOO@BAR.BUZ"}},
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
            {"is_admin": False, "user": {"name": "FOO", "email": "FOO@BAR.BUZ"}},
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/structure-members/{member.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["is_admin"], False)
        self.assertNotEqual(response.data["user"]["name"], "FOO")
        self.assertNotEqual(response.data["user"]["email"], "FOO@BAR.BUZ")

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

    # Creation
    def test_post_request_without_struct_empty(self):
        self.client.force_authenticate(user=self.me)
        response = self.client.post(
            "/structure-members/", {"user": {"name": "FOO", "email": "FOO@BAR.BUZ"}}
        )
        self.assertEquals(response.status_code, 403)

    def test_admin_user_can_invite_new_user(self):
        self.client.force_authenticate(user=self.me)

        response = self.client.post(
            f"/structure-members/?structure={self.my_struct.slug}",
            {"is_admin": False, "user": {"name": "FOO", "email": "FOO@BAR.BUZ"}},
        )
        self.assertEqual(response.status_code, 201)
        member = response.data["id"]
        response = self.client.get(f"/structure-members/{member}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["is_admin"], False)
        self.assertEqual(response.data["user"]["name"], "FOO")
        self.assertEqual(response.data["user"]["email"], "FOO@BAR.BUZ")

    def test_admin_user_cant_force_validation(self):
        self.client.force_authenticate(user=self.me)

        response = self.client.post(
            f"/structure-members/?structure={self.my_struct.slug}",
            {
                "is_admin": False,
                "is_valid": True,
                "user": {"name": "FOO", "email": "FOO@BAR.BUZ"},
            },
        )
        self.assertEqual(response.status_code, 201)
        member = response.data["id"]
        response = self.client.get(f"/structure-members/{member}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["is_valid"], False)

    def test_admin_user_can_invite_existing_user(self):
        self.client.force_authenticate(user=self.me)

        response = self.client.post(
            f"/structure-members/?structure={self.my_struct.slug}",
            {
                "is_admin": False,
                "user": {"name": "FOO", "email": f"{self.another_struct_user.email}"},
            },
        )
        self.assertEqual(response.status_code, 201)
        member = response.data["id"]
        response = self.client.get(f"/structure-members/{member}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["is_admin"], False)
        self.assertNotEqual(response.data["user"]["name"], "FOO")
        self.assertEqual(response.data["user"]["email"], self.another_struct_user.email)
        self.assertEqual(len(mail.outbox), 1)

    def test_anonymous_user_cant_invite_structure_members(self):
        response = self.client.post(
            f"/structure-members/?structure={self.my_struct.slug}",
            {
                "is_admin": False,
                "user": {"name": "FOO", "email": f"{self.another_struct_user.email}"},
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_standard_user_cant_invite_structure_members(self):
        self.client.force_authenticate(user=self.user2)
        response = self.client.post(
            f"/structure-members/?structure={self.my_struct.slug}",
            {
                "is_admin": False,
                "user": {"name": "FOO", "email": f"{self.another_struct_user.email}"},
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_super_user_can_invite_structure_members(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            f"/structure-members/?structure={self.my_struct.slug}",
            {
                "is_admin": False,
                "user": {"name": "FOO", "email": f"{self.another_struct_user.email}"},
            },
        )
        self.assertEqual(response.status_code, 201)
        member = response.data["id"]
        response = self.client.get(f"/structure-members/{member}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["is_admin"], False)
        self.assertNotEqual(response.data["user"]["name"], "FOO")
        self.assertEqual(response.data["user"]["email"], self.another_struct_user.email)
        self.assertEqual(len(mail.outbox), 1)

    def test_admin_can_reinvite_user(self):
        self.client.force_authenticate(user=self.me)
        user = baker.make("users.User")
        self.my_struct.members.add(user)
        member = user.membership.get(structure=self.my_struct)
        self.assertFalse(member.is_valid)
        response = self.client.post(
            f"/structure-members/{member.id}/resend-invite/",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Votre invitation sur DORA", mail.outbox[0].subject)

    def test_admin_cant_reinvite_valid_user(self):
        self.client.force_authenticate(user=self.me)
        user = baker.make("users.User")
        self.my_struct.members.add(user, through_defaults={"is_valid": True})
        member = user.membership.get(structure=self.my_struct)
        response = self.client.post(
            f"/structure-members/{member.id}/resend-invite/",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(mail.outbox), 0)

    def test_admin_cant_reinvite_user_to_other_struct(self):
        self.client.force_authenticate(user=self.me)
        user = baker.make("users.User")
        self.other_struct.members.add(user)
        member = user.membership.get(structure=self.other_struct)
        self.assertFalse(member.is_valid)
        response = self.client.post(
            f"/structure-members/{member.id}/resend-invite/",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(mail.outbox), 0)

    def test_anonymous_cant_reinvite_user(self):
        user = baker.make("users.User")
        self.my_struct.members.add(user)
        member = user.membership.get(structure=self.my_struct)
        self.assertFalse(member.is_valid)
        response = self.client.post(
            f"/structure-members/{member.id}/resend-invite/",
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(len(mail.outbox), 0)

    def test_standard_user_cant_reinvite_user(self):
        self.client.force_authenticate(user=self.user2)
        user = baker.make("users.User")
        self.my_struct.members.add(user)
        member = user.membership.get(structure=self.my_struct)
        self.assertFalse(member.is_valid)
        response = self.client.post(
            f"/structure-members/{member.id}/resend-invite/",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(mail.outbox), 0)

    def test_superuser_can_reinvite_user(self):
        self.client.force_authenticate(user=self.superuser)
        user = baker.make("users.User")
        self.my_struct.members.add(user)
        member = user.membership.get(structure=self.my_struct)
        self.assertFalse(member.is_valid)
        response = self.client.post(
            f"/structure-members/{member.id}/resend-invite/",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Votre invitation sur DORA", mail.outbox[0].subject)

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
