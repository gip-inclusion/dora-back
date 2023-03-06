from django.core import mail
from model_bakery import baker
from rest_framework.test import APITestCase

from dora.core.test_utils import make_service, make_structure
from dora.services.enums import ServiceStatus
from dora.structures.models import (
    Structure,
    StructureMember,
    StructurePutativeMember,
    StructureSource,
)

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
        # Structure dont je suis administrateur
        self.my_struct = make_structure()
        self.my_struct.members.add(
            self.me,
            through_defaults={
                "is_admin": True,
            },
        )
        # Structure dont je ne suis pas administrateur
        self.my_other_struct = make_structure(creator=None, last_editor=None)
        self.my_other_struct.members.add(self.me)

        # Structure dont je ne suis pas membre
        self.other_struct = make_structure()
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

    def test_can_edit_my_administered_structures(self):
        response = self.client.patch(
            f"/structures/{self.my_struct.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/structures/{self.my_struct.slug}/")
        self.assertEqual(response.data["name"], "xxx")

    def test_cant_edit_my_other_structures(self):
        response = self.client.patch(
            f"/structures/{self.my_other_struct.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 403)

    def test_cant_edit_other_structures(self):
        response = self.client.patch(
            f"/structures/{self.other_struct.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 403)

    def test_edit_structures_updates_last_editor(self):
        self.assertNotEqual(self.my_struct.last_editor, self.me)
        response = self.client.patch(
            f"/structures/{self.my_struct.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 200)
        slug = response.data["slug"]
        s = Structure.objects.get(slug=slug)
        self.assertEqual(s.last_editor, self.me)

    # def test_can_write_field_true(self):
    #     response = self.client.get(f"/structures/{self.my_struct.slug}/")
    #     self.assertEqual(response.status_code, 200)
    #     self.assertEqual(response.data["can_write"], True)

    # def test_can_write_field_false1(self):
    #     response = self.client.get(f"/structures/{self.my_other_struct.slug}/")
    #     self.assertEqual(response.status_code, 200)
    #     self.assertEqual(response.data["can_write"], False)

    # def test_can_write_field_false2(self):
    #     response = self.client.get(f"/structures/{self.other_struct.slug}/")
    #     self.assertEqual(response.status_code, 200)
    #     self.assertEqual(response.data["can_write"], False)

    def test_update_validate_accesslibre_url_rejected(self):
        response = self.client.patch(
            f"/structures/{self.my_struct.slug}/",
            {"accesslibre_url": "https://www.youtube.com"},
        )
        self.assertEqual(
            response.data.get("accesslibre_url")[0].get("message"),
            "L'URL doit débuter par https://acceslibre.beta.gouv.fr/",
        )
        self.assertEqual(response.status_code, 400)

    def test_update_validate_accesslibre_url_accepted(self):
        slug = self.my_struct.slug
        url = "https://acceslibre.beta.gouv.fr/app/75-paris/a/restaurant/erp/breizh-cafe-marais-la-crepe-autrement/"
        response = self.client.patch(f"/structures/{slug}/", {"accesslibre_url": url})

        self.assertEqual(response.status_code, 200)
        self.my_struct.refresh_from_db()

        response = self.client.get(f"/structures/{slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["accesslibre_url"], url)

    def test_update_validate_opening_hours_rejected(self):
        response = self.client.patch(
            f"/structures/{self.my_struct.slug}/",
            {"opening_hours": "xxx"},
        )
        self.assertEqual(
            response.data.get("opening_hours")[0].get("message"),
            "Le format des horaires d'ouverture est incorrect",
        )
        self.assertEqual(response.status_code, 400)

    def test_update_validate_opening_hours_accepted(self):
        slug = self.my_struct.slug
        opening_hours = "Mo-Fr 09:00-12:00,14:00-18:30; Sa 08:30-12:00"
        response = self.client.patch(
            f"/structures/{slug}/", {"opening_hours": opening_hours}
        )

        self.assertEqual(response.status_code, 200)
        self.my_struct.refresh_from_db()

        response = self.client.get(f"/structures/{slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["opening_hours"], opening_hours)

    def test_update_national_labels_accepted(self):
        slug = self.my_struct.slug
        national_labels = ["mobin", "pole-emploi"]
        response = self.client.patch(
            f"/structures/{slug}/",
            {"national_labels": national_labels},
        )

        self.assertEqual(response.status_code, 200)
        self.my_struct.refresh_from_db()

        response = self.client.get(f"/structures/{slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            sorted(response.data["national_labels"]), sorted(national_labels)
        )

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

    # def test_manager_can_edit_everything_in_its_dept(self):
    #     assert False
    #     self.client.force_authenticate(user=self.superuser)
    #     response = self.client.patch(
    #         f"/structures/{self.my_struct.slug}/", {"name": "xxx"}
    #     )
    #     self.assertEqual(response.status_code, 200)
    #     response = self.client.get(f"/structures/{self.my_struct.slug}/")
    #     self.assertEqual(response.data["name"], "xxx")

    # def test_manager_cant_edit_outside_its_dept(self):
    #     assert False

    # def test_superuser_can_write_field_true(self):
    #     self.client.force_authenticate(user=self.superuser)
    #     response = self.client.get(f"/structures/{self.my_struct.slug}/")
    #     self.assertEqual(response.status_code, 200)
    #     self.assertEqual(response.data["can_write"], True)

    # def test_manager_can_write_field_true_inside_its_dept(self):
    #     assert False

    # def test_manager_can_write_field_false_outside_its_dept(self):
    #     assert False

    def test_bizdev_cant_edit_everything(self):
        self.client.force_authenticate(user=self.bizdev)
        response = self.client.patch(
            f"/structures/{self.my_struct.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 403)

    # def test_bizdev_can_write_field_false(self):
    #     self.client.force_authenticate(user=self.bizdev)
    #     response = self.client.get(f"/structures/{self.my_struct.slug}/")
    #     self.assertEqual(response.status_code, 200)
    #     self.assertEqual(response.data["can_write"], False)

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
        self.assertEqual(s.source, StructureSource.objects.get(value="porteur"))

    def test_adding_structure_by_superuser_sets_source(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            "/structures/",
            DUMMY_STRUCTURE,
        )
        self.assertEqual(response.status_code, 201)
        slug = response.data["slug"]
        s = Structure.objects.get(slug=slug)
        self.assertEqual(s.source, StructureSource.objects.get(value="equipe-dora"))

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


class StructureSiteMapTestCase(APITestCase):
    def test_structures_wo_published_services_are_not_listed(self):
        st = make_structure()
        make_service(structure=st, status=ServiceStatus.DRAFT)
        make_service(structure=st, status=ServiceStatus.ARCHIVED)

        response = self.client.get("/structures/?active=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_structures_w_published_services_are_listed(self):
        st = make_structure()
        make_service(structure=st, status=ServiceStatus.DRAFT)
        make_service(structure=st, status=ServiceStatus.PUBLISHED)

        response = self.client.get("/structures/?active=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)


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

        self.my_struct = make_structure()
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

        self.my_other_struct = make_structure(creator=None, last_editor=None)
        self.my_other_struct.members.add(
            self.me,
            through_defaults={
                "is_admin": True,
            },
        )
        self.my_other_struct.members.add(self.my_other_struct_user)

        self.other_struct = make_structure()
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
        self.assertEquals(response.status_code, 400)

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

    # def test_manager_can_see_structure_members_in_its_depts(self):
    #     assert False

    # def test_manager_cant_see_structure_members_outside_its_depts(self):
    #     assert False

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
        self.assertEqual(response.status_code, 401)

    def test_standard_user_can_see_structure_members(self):
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(
            f"/structure-members/?structure={self.my_struct.slug}"
        )
        self.assertEqual(response.status_code, 200)
        emails = [m["user"]["email"] for m in response.data]
        self.assertIn(self.me.email, emails)
        self.assertIn(self.user1.email, emails)
        self.assertIn(self.user2.email, emails)

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

    # def test_manager_can_see_structure_member_in_its_depts(self):
    #     assert False

    # def test_manager_cant_see_structure_member_outside_its_depts(self):
    #     assert False

    def test_unaccepted_admin_user_cant_see_structure_member(self):
        self.client.force_authenticate(user=self.unaccepted_admin)
        member = self.user1.membership.get(structure=self.my_struct)
        response = self.client.get(f"/structure-members/{member.id}/")
        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_cant_see_structure_member(self):
        member = self.user1.membership.get(structure=self.my_struct)
        response = self.client.get(f"/structure-members/{member.id}/")
        self.assertEqual(response.status_code, 401)

    def test_standard_user_can_see_structure_member(self):
        self.client.force_authenticate(user=self.user2)
        member = self.user1.membership.get(structure=self.my_struct)
        response = self.client.get(f"/structure-members/{member.id}/")
        self.assertEqual(response.status_code, 200)

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

    # def test_manager_cant_change_structure_members_in_its_depts(self):
    #     assert False

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
        self.assertEqual(response.status_code, 401)

    def test_standard_user_cant_change_structure_members(self):
        self.client.force_authenticate(user=self.user2)
        member = self.user1.membership.get(structure=self.my_struct)
        response = self.client.patch(
            f"/structure-members/{member.id}/",
            {"is_admin": False, "user": {"last_name": "FOO", "email": "FOO@BAR.BUZ"}},
        )
        self.assertEqual(response.status_code, 403)

    def test_standard_user_cant_gain_admin_privilege(self):
        self.client.force_authenticate(user=self.user2)
        member = self.user2.membership.get(structure=self.my_struct)
        self.assertFalse(member.is_admin)
        response = self.client.patch(
            f"/structure-members/{member.id}/",
            {"is_admin": True},
        )
        self.assertEqual(response.status_code, 403)

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

    # def test_manager_cant_delete_structure_members_in_its_depts(self):
    #     assert False

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
        self.assertEqual(response.status_code, 401)

    def test_standard_user_cant_delete_structure_members(self):
        self.client.force_authenticate(user=self.user2)
        member = self.user1.membership.get(structure=self.my_struct)
        response = self.client.delete(
            f"/structure-members/{member.id}/",
        )
        self.assertEqual(response.status_code, 403)

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

    # def test_manager_can_invite_first_admin_in_its_depts(self):
    #     assert False

    # def test_manager_can_invite_members_in_its_depts(self):
    #     # after the first admin
    #     assert False

    # def test_manager_cant_invite_outside_its_depts(self):
    #     assert False

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

    def test_bizdev_can_invite_structure_members(self):
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
        self.assertEqual(response.status_code, 201)
        member = response.data["id"]
        response = self.client.get(f"/structure-putative-members/{member}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["is_admin"], False)
        self.assertNotEqual(response.data["user"]["last_name"], "FOO")
        self.assertEqual(response.data["user"]["email"], self.another_struct_user.email)
        self.assertEqual(len(mail.outbox), 1)

    def test_admin_can_resend_invite_to_user(self):
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

    # def test_manager_can_resend_invite_to_first_invited_admin(self):
    #     assert False

    def test_admin_cant_resend_invite_to_valid_member(self):
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

    def test_admin_can_resend_invite_to_valid_user_with_no_pw_set(self):
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

    def test_admin_cant_resend_invite_to_user_to_other_struct(self):
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

    def test_anonymous_cant_resend_invite_to_user(self):
        user = baker.make("users.User", is_valid=True)
        pm = StructurePutativeMember.objects.create(
            user=user, structure=self.my_struct, invited_by_admin=True
        )
        response = self.client.post(
            f"/structure-putative-members/{pm.id}/resend-invite/",
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(len(mail.outbox), 0)

    def test_standard_user_cant_resend_invite_to_user(self):
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

    def test_superuser_can_resend_invite_to_user(self):
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

    def test_bizdev_cant_resend_invite_to_user(self):
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
        member.refresh_from_db()
        self.assertFalse(member.is_admin)

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

    def test_user_can_accept_invitation(self):

        # Invitation
        admin = baker.make("users.User", is_valid=True)
        structure = make_structure()
        baker.make("Establishment", siret=structure.siret)
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
                    "email": "FOO@BAR.BUZ",
                },
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        self.client.force_authenticate(user=None)
        pm = StructurePutativeMember.objects.get(pk=response.data["id"])
        mail.outbox = []

        # Acceptation
        self.client.force_authenticate(user=pm.user)
        response = self.client.post(
            "/auth/join-structure/",
            {
                "siret": structure.siret,
            },
        )
        with self.assertRaises(StructurePutativeMember.DoesNotExist):
            StructurePutativeMember.objects.get(pk=pm.pk)
        member = StructureMember.objects.get(structure=structure, user=pm.user)
        self.assertFalse(member.is_admin)

    def test_admin_notified_when_invitation_accepted(self):
        baker.make("Establishment", siret=self.my_struct.siret)

        # Invitation
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
        self.assertEqual(len(mail.outbox), 1)

        # Reset
        mail.outbox = []

        # Acceptation
        self.client.force_authenticate(user=self.another_struct_user)
        response = self.client.post(
            "/auth/join-structure/",
            {
                "siret": self.my_struct.siret,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(mail.outbox), 0)
        self.assertIn("Invitation acceptée", mail.outbox[0].subject)
        self.assertIn(self.another_struct_user.email, mail.outbox[0].body)

    # def test_manager_notified_when_its_invitation_was_accepted(self):
    #     assert False

    def test_admin_notified_when_new_user_request_access(self):
        baker.make("Establishment", siret=self.my_struct.siret)
        user = baker.make("users.User", is_valid=True)

        self.client.force_authenticate(user=user)
        response = self.client.post(
            "/auth/join-structure/",
            {
                "siret": self.my_struct.siret,
            },
        )
        self.assertEqual(response.status_code, 200)
        StructurePutativeMember.objects.get(
            structure__siret=self.my_struct.siret, user=user
        )
        self.assertGreater(len(mail.outbox), 0)
        self.assertIn("Demande d’accès à votre structure", mail.outbox[0].subject)
        self.assertIn(self.my_struct.slug, mail.outbox[0].body)
