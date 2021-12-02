from datetime import timedelta

from django.utils import timezone
from model_bakery import baker
from rest_framework.test import APITestCase

from dora.structures.models import Structure

from .models import AccessCondition, Service, ServiceModificationHistoryItem

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
        self.global_condition1 = baker.make("AccessCondition", structure=None)
        self.global_condition2 = baker.make("AccessCondition", structure=None)
        self.struct_condition1 = baker.make("AccessCondition", structure=self.my_struct)
        self.struct_condition2 = baker.make("AccessCondition", structure=self.my_struct)
        self.other_struct_condition1 = baker.make(
            "AccessCondition", structure=baker.make("Structure")
        )
        self.other_struct_condition2 = baker.make(
            "AccessCondition", structure=baker.make("Structure")
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

    def test_anonymous_user_cant_see_drafts(self):
        self.client.force_authenticate(user=None)
        service = baker.make(
            "Service",
            is_draft=True,
        )
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 404)

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
        draft_service = Service.objects.get(pk=draft_service.pk)
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
        slug = baker.make("Structure").slug
        Structure.objects.get(slug=slug)
        DUMMY_SERVICE["structure"] = slug
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

    # CustomizableChoices
    def test_anonymous_user_see_global_choices(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(
            "/services-options/",
        )
        conds = [d["value"] for d in response.data["access_conditions"]]
        self.assertIn(self.global_condition1.id, conds)
        self.assertIn(self.global_condition2.id, conds)

    def test_everybody_see_global_choices(self):
        response = self.client.get(
            "/services-options/",
        )
        conds = [d["value"] for d in response.data["access_conditions"]]
        self.assertIn(self.global_condition1.id, conds)
        self.assertIn(self.global_condition2.id, conds)

    def test_everybody_see_his_struct_choices(self):
        response = self.client.get(
            "/services-options/",
        )
        conds = [d["value"] for d in response.data["access_conditions"]]
        self.assertIn(self.struct_condition1.id, conds)
        self.assertIn(self.struct_condition2.id, conds)

    def test_nobody_sees_other_structs_choices(self):
        response = self.client.get(
            "/services-options/",
        )
        conds = [d["value"] for d in response.data["access_conditions"]]
        self.assertNotIn(self.other_struct_condition1.id, conds)
        self.assertNotIn(self.other_struct_condition2.id, conds)

    def test_admin_sees_all_choices(self):
        self.client.force_authenticate(user=self.superuser)

        response = self.client.get(
            "/services-options/",
        )
        conds = [d["value"] for d in response.data["access_conditions"]]

        self.assertIn(self.global_condition1.id, conds)
        self.assertIn(self.global_condition2.id, conds)
        self.assertIn(self.struct_condition1.id, conds)
        self.assertIn(self.struct_condition2.id, conds)
        self.assertIn(self.other_struct_condition1.id, conds)
        self.assertIn(self.other_struct_condition2.id, conds)

    def test_can_add_global_choice(self):
        response = self.client.patch(
            f"/services/{self.my_service.slug}/",
            {"access_conditions": [self.global_condition1.id]},
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/services/{self.my_service.slug}/")
        self.assertEqual(
            response.data["access_conditions"], [self.global_condition1.id]
        )

    def test_can_add_structure_choice(self):
        response = self.client.patch(
            f"/services/{self.my_service.slug}/",
            {"access_conditions": [self.struct_condition1.id]},
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/services/{self.my_service.slug}/")
        self.assertEqual(
            response.data["access_conditions"], [self.struct_condition1.id]
        )

    def test_cant_add_other_structure_choice(self):
        response = self.client.patch(
            f"/services/{self.my_service.slug}/",
            {"access_conditions": [self.other_struct_condition1.id]},
        )
        self.assertEqual(response.status_code, 400)

    def test_cant_add_other_structure_choice_even_if_mine(self):
        struct = baker.make("Structure")
        struct.members.add(self.me)
        struct_condition = baker.make("AccessCondition", structure=struct)
        response = self.client.patch(
            f"/services/{self.my_service.slug}/",
            {"access_conditions": [struct_condition.id]},
        )
        self.assertEqual(response.status_code, 400)

    def test_can_add_new_choice_on_update(self):

        num_access_conditions = AccessCondition.objects.all().count()

        response = self.client.patch(
            f"/services/{self.my_service.slug}/",
            {"access_conditions": ["foobar"]},
        )

        self.assertEqual(response.status_code, 200)
        slug = response.data["slug"]
        service = Service.objects.get(slug=slug)

        new_num_access_conditions = AccessCondition.objects.all().count()
        self.assertEqual(new_num_access_conditions - num_access_conditions, 1)
        foobar = AccessCondition.objects.filter(name="foobar").first()
        self.assertEqual(foobar.structure, self.my_struct)
        self.assertEqual(service.access_conditions.first(), foobar)

    def test_can_add_new_choice_on_create(self):
        num_access_conditions = AccessCondition.objects.all().count()

        DUMMY_SERVICE["structure"] = self.my_struct.slug
        DUMMY_SERVICE["access_conditions"] = ["foobar"]
        response = self.client.post(
            "/services/",
            DUMMY_SERVICE,
        )
        self.assertEqual(response.status_code, 201)
        slug = response.data["slug"]
        service = Service.objects.get(slug=slug)

        new_num_access_conditions = AccessCondition.objects.all().count()
        self.assertEqual(new_num_access_conditions - num_access_conditions, 1)
        foobar = AccessCondition.objects.filter(name="foobar").first()
        self.assertEqual(foobar.structure, self.my_struct)
        self.assertEqual(service.access_conditions.first(), foobar)

    def test_cant_add_empty_choice(self):
        response = self.client.patch(
            f"/services/{self.my_service.slug}/",
            {"access_conditions": [""]},
        )
        self.assertEqual(response.status_code, 400)

    def test_cant_add_very_long_choice(self):
        val = "." * 141
        response = self.client.patch(
            f"/services/{self.my_service.slug}/",
            {"access_conditions": [val]},
        )
        self.assertEqual(response.status_code, 400)

    # Confidentiality
    def test_anonymous_user_can_see_public_contact_info(self):
        self.client.force_authenticate(user=None)
        service = baker.make(
            "Service",
            is_draft=False,
            contact_name="FOO",
            contact_phone="1234",
            contact_email="foo@bar.buz",
            is_contact_info_public=True,
        )
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.data["contact_name"], "FOO")
        self.assertEqual(response.data["contact_phone"], "1234")
        self.assertEqual(response.data["contact_email"], "foo@bar.buz")

    def test_anonymous_user_cant_see_private_contact_info(self):
        self.client.force_authenticate(user=None)
        service = baker.make(
            "Service",
            is_draft=False,
            contact_name="FOO",
            contact_phone="1234",
            contact_email="foo@bar.buz",
            is_contact_info_public=False,
        )
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.data["contact_name"], "")
        self.assertEqual(response.data["contact_phone"], "")
        self.assertEqual(response.data["contact_email"], "")

    def test_logged_user_can_see_public_contact_info(self):
        service = baker.make(
            "Service",
            is_draft=False,
            contact_name="FOO",
            contact_phone="1234",
            contact_email="foo@bar.buz",
            is_contact_info_public=True,
        )
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.data["contact_name"], "FOO")
        self.assertEqual(response.data["contact_phone"], "1234")
        self.assertEqual(response.data["contact_email"], "foo@bar.buz")

    def test_logged_user_can_see_private_contact_info(self):
        service = baker.make(
            "Service",
            is_draft=False,
            contact_name="FOO",
            contact_phone="1234",
            contact_email="foo@bar.buz",
            is_contact_info_public=False,
        )
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.data["contact_name"], "FOO")
        self.assertEqual(response.data["contact_phone"], "1234")
        self.assertEqual(response.data["contact_email"], "foo@bar.buz")

    # Modifications
    def test_is_draft_by_default(self):
        service = baker.make(
            "Service",
        )
        self.assertTrue(service.is_draft)

    def test_publishing_updates_publication_date(self):
        service = baker.make("Service", is_draft=True, structure=self.my_struct)
        self.assertIsNone(service.publication_date)
        response = self.client.patch(f"/services/{service.slug}/", {"is_draft": False})
        self.assertEqual(response.status_code, 200)
        service.refresh_from_db()
        self.assertFalse(service.is_draft)
        self.assertIsNotNone(service.publication_date)
        self.assertTrue(
            timezone.now() - service.publication_date < timedelta(seconds=1)
        )

    def test_updating_without_publishing_doesnt_update_publication_date(self):
        service = baker.make("Service", is_draft=True, structure=self.my_struct)
        self.assertIsNone(service.publication_date)
        response = self.client.patch(f"/services/{service.slug}/", {"name": "xxx"})
        self.assertEqual(response.status_code, 200)
        service.refresh_from_db()
        self.assertTrue(service.is_draft)
        self.assertIsNone(service.publication_date)

    # History logging
    def test_editing_log_change(self):
        self.assertFalse(ServiceModificationHistoryItem.objects.exists())
        response = self.client.patch(
            f"/services/{self.my_service.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ServiceModificationHistoryItem.objects.exists())
        hitem = ServiceModificationHistoryItem.objects.all()[0]
        self.assertEqual(hitem.user, self.me)
        self.assertEqual(hitem.service, self.my_service)
        self.assertEqual(hitem.fields, ["name"])
        self.assertTrue(timezone.now() - hitem.date < timedelta(seconds=1))

    def test_editing_log_multiple_change(self):
        self.client.patch(
            f"/services/{self.my_service.slug}/", {"name": "xxx", "address1": "yyy"}
        )
        hitem = ServiceModificationHistoryItem.objects.all()[0]
        self.assertEqual(hitem.fields, ["name", "address1"])

    def test_editing_log_m2m_change(self):
        response = self.client.patch(
            f"/services/{self.my_service.slug}/", {"access_conditions": ["xxx"]}
        )
        self.assertEqual(response.status_code, 200)
        hitem = ServiceModificationHistoryItem.objects.all()[0]
        self.assertEqual(
            hitem.fields,
            [
                "access_conditions",
            ],
        )

    def test_creating_draft_doesnt_log_changes(self):
        DUMMY_SERVICE["structure"] = self.my_struct.slug
        response = self.client.post(
            "/services/",
            DUMMY_SERVICE,
        )
        self.assertEqual(response.status_code, 201)
        self.assertFalse(ServiceModificationHistoryItem.objects.exists())

    def test_editing_doesnt_log_draft_changes(self):
        response = self.client.patch(
            f"/services/{self.my_draft_service.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ServiceModificationHistoryItem.objects.exists())


class ServiceSearchTextCase(APITestCase):
    def test_can_see_published_services(self):
        service = baker.make("Service", is_draft=False)
        response = self.client.get("/search/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service.slug)

    def test_cant_see_draft_services(self):
        baker.make("Service", is_draft=True)
        response = self.client.get("/search/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_can_see_service_with_future_suspension_date(self):
        service = baker.make(
            "Service",
            is_draft=False,
            suspension_date=timezone.now() + timedelta(days=1),
        )
        response = self.client.get("/search/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service.slug)

    def test_cannot_see_service_with_past_suspension_date(self):
        baker.make(
            "Service",
            is_draft=False,
            suspension_date=timezone.now() - timedelta(days=1),
        )
        response = self.client.get("/search/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)
