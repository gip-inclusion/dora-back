from model_bakery import baker
from rest_framework.test import APITestCase

from .models import Service

DUMMY_SERVICE = {"name": "Mon service"}


class ServiceTestCase(APITestCase):
    def setUp(self):
        self.me = baker.make("users.User")
        self.superuser = baker.make("users.User", is_staff=True)
        self.my_struct = baker.make("Structure")
        self.my_struct.members.add(self.me)
        self.my_service = baker.make(
            "Service", structure=self.my_struct, is_draft=False, creator=self.me
        )
        self.my_draft_service = baker.make(
            "Service", structure=self.my_struct, is_draft=True, creator=self.me
        )
        self.my_latest_draft_service = baker.make(
            "Service", structure=self.my_struct, is_draft=True, creator=self.me
        )

        self.other_service = baker.make("Service", is_draft=False)
        self.other_draft_service = baker.make("Service", is_draft=True)

        self.colleague_service = baker.make(
            "Service", structure=self.my_struct, is_draft=False
        )
        self.colleague_draft_service = baker.make(
            "Service", structure=self.my_struct, is_draft=True
        )
        self.client.force_authenticate(user=self.me)

    # Visibility

    def test_can_see_my_services(self):
        response = self.client.get("/services/")
        services_ids = [s["slug"] for s in response.data]
        self.assertIn(self.my_service.slug, services_ids)

    def test_can_see_my_drafts(self):
        response = self.client.get("/services/")
        services_ids = [s["slug"] for s in response.data]
        self.assertIn(self.my_draft_service.slug, services_ids)
        self.assertIn(self.my_latest_draft_service.slug, services_ids)

    def test_can_see_colleague_services(self):
        response = self.client.get("/services/")
        services_ids = [s["slug"] for s in response.data]
        self.assertIn(self.colleague_service.slug, services_ids)

    def test_can_see_colleague_draft_services(self):
        response = self.client.get("/services/")
        services_ids = [s["slug"] for s in response.data]
        self.assertIn(self.colleague_draft_service.slug, services_ids)

    def test_can_see_others_services(self):
        response = self.client.get("/services/")
        services_ids = [s["slug"] for s in response.data]
        self.assertIn(self.other_service.slug, services_ids)

    def test_cant_see_others_drafts(self):
        response = self.client.get("/services/")
        services_ids = [s["slug"] for s in response.data]
        self.assertNotIn(self.other_draft_service, services_ids)

    # Modification

    def test_can_edit_my_services(self):
        response = self.client.patch(
            f"/services/{self.my_service.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/services/{self.my_service.slug}/")
        self.assertEqual(response.data["name"], "xxx")

    def test_can_edit_my_draft_services(self):
        response = self.client.patch(
            f"/services/{self.my_draft_service.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/services/{self.my_draft_service.slug}/")
        self.assertEqual(response.data["name"], "xxx")

    def test_can_edit_colleague_services(self):
        response = self.client.patch(
            f"/services/{self.colleague_service.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/services/{self.colleague_service.slug}/")
        self.assertEqual(response.data["name"], "xxx")

    def test_can_edit_colleague_draft_services(self):
        response = self.client.patch(
            f"/services/{self.colleague_draft_service.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/services/{self.colleague_draft_service.slug}/")
        self.assertEqual(response.data["name"], "xxx")

    def test_cant_edit_others_services(self):
        response = self.client.patch(
            f"/services/{self.other_service.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 403)

    def test_cant_edit_others_draft_services(self):
        response = self.client.patch(
            f"/services/{self.other_draft_service.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 404)

    def test_edit_structures_updates_last_editor(self):
        self.assertNotEqual(self.colleague_service.last_editor, self.me)
        response = self.client.patch(
            f"/services/{self.colleague_service.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 200)
        slug = response.data["slug"]
        s = Service.objects.get(slug=slug)
        self.assertEqual(s.last_editor, self.me)
        self.assertNotEqual(s.creator, self.me)

    def test_can_write_field_true(self):
        response = self.client.get(f"/services/{self.my_service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["can_write"], True)
        response = self.client.get(f"/services/{self.my_draft_service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["can_write"], True)

    def test_can_write_field_false(self):
        response = self.client.get(f"/services/{self.other_service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["can_write"], False)

    # Last draft

    def test_get_last_draft_returns_only_mine(self):
        response = self.client.get("/services/last-draft/")
        self.assertEqual(response.data["slug"], self.my_latest_draft_service.slug)

    def test_get_last_draft_only_if_still_in_struct(self):
        draft_service = baker.make(
            "Service", structure=self.my_struct, is_draft=True, creator=self.me
        )
        response = self.client.get("/services/last-draft/")
        self.assertEqual(response.data["slug"], draft_service.slug)
        draft_service.structure = baker.make("Structure")
        draft_service.save()
        response = self.client.get("/services/last-draft/")
        self.assertEqual(response.data["slug"], self.my_latest_draft_service.slug)

    def test_superuser_get_last_draft_any_struct(self):
        self.client.force_authenticate(user=self.superuser)
        service = baker.make("Service", is_draft=True, creator=self.superuser)
        response = self.client.get("/services/last-draft/")
        self.assertEqual(response.data["slug"], service.slug)

    # Superuser

    def test_superuser_can_sees_everything(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get("/services/")
        services_ids = [s["slug"] for s in response.data]
        self.assertIn(self.my_service.slug, services_ids)
        self.assertIn(self.my_draft_service.slug, services_ids)
        self.assertIn(self.other_service.slug, services_ids)
        self.assertNotIn(self.other_draft_service, services_ids)

    def test_superuser_can_edit_everything(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.patch(
            f"/services/{self.my_draft_service.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/services/{self.my_draft_service.slug}/")
        self.assertEqual(response.data["name"], "xxx")

    def test_superuser_last_draft_doesnt_return_others(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get("/services/last-draft/")
        self.assertEqual(response.status_code, 404)

    def test_superuser_can_write_field_true(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(f"/services/{self.my_service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["can_write"], True)

    # Adding

    def test_can_add_service(self):
        DUMMY_SERVICE["structure"] = self.my_struct.slug
        response = self.client.post(
            "/services/",
            DUMMY_SERVICE,
        )
        self.assertEqual(response.status_code, 201)
        slug = response.data["slug"]
        Service.objects.get(slug=slug)

    def test_add_service_check_structure(self):
        DUMMY_SERVICE["structure"] = baker.make("Structure").slug
        response = self.client.post(
            "/services/",
            DUMMY_SERVICE,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["structure"][0]["code"], "not_member_of_struct")

    def test_super_user_can_add_to_any_structure(self):
        self.client.force_authenticate(user=self.superuser)
        DUMMY_SERVICE["structure"] = baker.make("Structure").slug
        response = self.client.post(
            "/services/",
            DUMMY_SERVICE,
        )
        self.assertEqual(response.status_code, 201)
        slug = response.data["slug"]
        Service.objects.get(slug=slug)

    def test_adding_service_populates_creator_last_editor(self):
        DUMMY_SERVICE["structure"] = self.my_struct.slug
        response = self.client.post(
            "/services/",
            DUMMY_SERVICE,
        )
        self.assertEqual(response.status_code, 201)
        slug = response.data["slug"]
        new_service = Service.objects.get(slug=slug)
        self.assertEqual(new_service.creator, self.me)
        self.assertEqual(new_service.last_editor, self.me)

    # Deleting

    def test_cant_delete_service(self):
        # Deletion is forbidden for now
        response = self.client.delete(
            f"/services/{self.my_service.slug}/",
        )
        self.assertEqual(response.status_code, 403)

    # get_my_services
    def test_filter_my_services_only(self):
        response = self.client.get("/services/?mine=1")
        services_ids = [s["slug"] for s in response.data]
        self.assertIn(self.my_service.slug, services_ids)
        self.assertIn(self.my_draft_service.slug, services_ids)
        self.assertIn(self.my_latest_draft_service.slug, services_ids)
        self.assertIn(self.colleague_service.slug, services_ids)
        self.assertIn(self.colleague_draft_service.slug, services_ids)
        self.assertNotIn(self.other_service.slug, services_ids)
        self.assertNotIn(self.other_draft_service, services_ids)
