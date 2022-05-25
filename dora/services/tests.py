from datetime import timedelta

from django.contrib.gis.geos import MultiPolygon, Point
from django.utils import timezone
from model_bakery import baker
from rest_framework.test import APITestCase

from dora.admin_express.models import AdminDivisionType
from dora.core.test_utils import make_service, make_structure
from dora.services.utils import (
    SYNC_CUSTOM_M2M_FIELDS,
    SYNC_FIELDS,
    SYNC_M2M_FIELDS,
    copy_service,
)
from dora.structures.models import Structure

from .models import (
    AccessCondition,
    LocationKind,
    Service,
    ServiceCategory,
    ServiceKind,
    ServiceModificationHistoryItem,
)

DUMMY_SERVICE = {"name": "Mon service"}


class ServiceTestCase(APITestCase):
    def setUp(self):
        self.me = baker.make("users.User", is_valid=True)
        self.unaccepted_user = baker.make("users.User", is_valid=True)
        self.superuser = baker.make("users.User", is_staff=True, is_valid=True)
        self.bizdev = baker.make("users.User", is_bizdev=True, is_valid=True)
        self.my_struct = make_structure(self.me)

        self.my_service = make_service(
            structure=self.my_struct, is_draft=False, creator=self.me
        )
        self.my_draft_service = make_service(
            structure=self.my_struct, is_draft=True, creator=self.me
        )
        self.my_latest_draft_service = make_service(
            structure=self.my_struct, is_draft=True, creator=self.me
        )

        self.other_service = make_service(is_draft=False)
        self.other_draft_service = make_service(is_draft=True)

        self.colleague_service = make_service(structure=self.my_struct, is_draft=False)
        self.colleague_draft_service = make_service(
            structure=self.my_struct, is_draft=True
        )
        self.global_condition1 = baker.make("AccessCondition", structure=None)
        self.global_condition2 = baker.make("AccessCondition", structure=None)
        self.struct_condition1 = baker.make("AccessCondition", structure=self.my_struct)
        self.struct_condition2 = baker.make("AccessCondition", structure=self.my_struct)
        self.other_struct_condition1 = baker.make(
            "AccessCondition",
            structure=make_structure(),
        )
        self.other_struct_condition2 = baker.make(
            "AccessCondition",
            structure=make_structure(),
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
        service = make_service(
            is_draft=True,
        )
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 404)

    def test_cant_see_draft_if_not_accepted_by_admin(self):
        self.client.force_authenticate(user=self.unaccepted_user)
        service = make_service(
            structure=self.my_struct,
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

    def test_cant_edit_colleague_services_if_not_accepted_by_admin(self):
        self.client.force_authenticate(user=self.unaccepted_user)
        response = self.client.patch(
            f"/services/{self.colleague_service.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 403)
        response = self.client.get(f"/services/{self.colleague_service.slug}/")
        self.assertNotEqual(response.data["name"], "xxx")

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
        draft_service = make_service(
            structure=self.my_struct, is_draft=True, creator=self.me
        )
        response = self.client.get("/services/last-draft/")
        self.assertEqual(response.data["slug"], draft_service.slug)
        draft_service = Service.objects.get(pk=draft_service.pk)
        draft_service.structure = make_structure()
        draft_service.save()
        response = self.client.get("/services/last-draft/")
        self.assertEqual(response.data["slug"], self.my_latest_draft_service.slug)

    def test_superuser_get_last_draft_any_struct(self):
        self.client.force_authenticate(user=self.superuser)
        service = make_service(is_draft=True, creator=self.superuser)
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

    def test_bizdev_cant_sees_everything(self):
        self.client.force_authenticate(user=self.bizdev)
        response = self.client.get("/services/")
        services_ids = [s["slug"] for s in response.data]
        self.assertIn(self.my_service.slug, services_ids)
        self.assertNotIn(self.my_draft_service.slug, services_ids)
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

    def test_bizdev_cant_edit_everything(self):
        self.client.force_authenticate(user=self.bizdev)
        response = self.client.patch(
            f"/services/{self.my_service.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 403)

    def test_superuser_last_draft_doesnt_return_others(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get("/services/last-draft/")
        self.assertEqual(response.status_code, 404)

    def test_superuser_can_write_field_true(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(f"/services/{self.my_service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["can_write"], True)

    def test_bizdev_can_write_field_false(self):
        self.client.force_authenticate(user=self.bizdev)
        response = self.client.get(f"/services/{self.my_service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["can_write"], False)

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

    def test_cant_add_service_if_not_accepted_by_admin(self):
        self.client.force_authenticate(user=self.unaccepted_user)
        DUMMY_SERVICE["structure"] = self.my_struct.slug
        response = self.client.post(
            "/services/",
            DUMMY_SERVICE,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["structure"][0]["code"], "not_member_of_struct")

    def test_add_service_check_structure(self):
        DUMMY_SERVICE["structure"] = baker.make(
            "Structure", _fill_optional=["siret"]
        ).slug
        response = self.client.post(
            "/services/",
            DUMMY_SERVICE,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["structure"][0]["code"], "not_member_of_struct")

    def test_super_user_can_add_to_any_structure(self):
        self.client.force_authenticate(user=self.superuser)
        slug = make_structure().slug
        Structure.objects.get(slug=slug)
        DUMMY_SERVICE["structure"] = slug
        response = self.client.post(
            "/services/",
            DUMMY_SERVICE,
        )
        self.assertEqual(response.status_code, 201)
        slug = response.data["slug"]
        Service.objects.get(slug=slug)

    def test_bizdev_cant_add_to_any_structure(self):
        self.client.force_authenticate(user=self.bizdev)
        slug = make_structure().slug
        Structure.objects.get(slug=slug)
        DUMMY_SERVICE["structure"] = slug
        response = self.client.post(
            "/services/",
            DUMMY_SERVICE,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["structure"][0]["code"], "not_member_of_struct")

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

    def test_superuser_sees_all_choices(self):
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

    def test_bizdev_sees_all_choices(self):
        self.client.force_authenticate(user=self.bizdev)

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
        struct = make_structure(self.me)
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
        service = make_service(
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
        service = make_service(
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
        service = make_service(
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

    def test_logged_user_can_see_public_contact_info_if_not_accepted_by_admin(self):
        self.client.force_authenticate(user=self.unaccepted_user)
        service = make_service(
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
        service = make_service(
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

    def test_nonvalidated_user_cant_see_private_contact_info(self):
        self.me.is_valid = False
        service = make_service(
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

    def test_logged_user_cant_see_public_contact_info_if_not_accepted_by_admin(self):
        self.client.force_authenticate(user=self.unaccepted_user)
        service = make_service(
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

    # Modifications
    def test_is_draft_by_default(self):
        service = make_service()
        self.assertTrue(service.is_draft)

    def test_publishing_updates_publication_date(self):
        service = make_service(is_draft=True, structure=self.my_struct)
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
        service = make_service(is_draft=True, structure=self.my_struct)
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

    def test_members_see_all_services_count(self):
        user = baker.make("users.User", is_valid=True)
        structure = make_structure(user)
        service = make_service(is_draft=False, structure=structure)
        make_service(is_draft=False, structure=structure)
        make_service(is_draft=True, structure=structure)
        self.client.force_authenticate(user=user)
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["structure_info"]["num_services"], 3)

    def test_su_see_all_services_count(self):
        user = baker.make("users.User", is_valid=True)
        structure = make_structure(user)
        service = make_service(is_draft=False, structure=structure)
        make_service(is_draft=False, structure=structure)
        make_service(is_draft=True, structure=structure)
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["structure_info"]["num_services"], 3)

    def test_others_see_public_services_count(self):
        user = baker.make("users.User", is_valid=True)
        user2 = baker.make("users.User", is_valid=True)
        structure = make_structure(user)
        service = make_service(is_draft=False, structure=structure)
        make_service(is_draft=False, structure=structure)
        make_service(is_draft=True, structure=structure)
        self.client.force_authenticate(user=user2)
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["structure_info"]["num_services"], 2)

    def test_anon_see_public_services_count(self):
        user = baker.make("users.User", is_valid=True)
        structure = make_structure(user)
        service = make_service(is_draft=False, structure=structure)
        make_service(is_draft=False, structure=structure)
        make_service(is_draft=True, structure=structure)
        self.client.force_authenticate(None)
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["structure_info"]["num_services"], 2)


class ServiceSearchTestCase(APITestCase):
    def setUp(self):
        self.region = baker.make("Region", code="99")
        self.dept = baker.make("Department", region=self.region.code, code="77")
        self.epci11 = baker.make("EPCI", code="11111")
        self.epci12 = baker.make("EPCI", code="22222")
        self.city1 = baker.make(
            "City",
            code="12345",
            epcis=[self.epci11.code, self.epci12.code],
            department=self.dept.code,
            region=self.region.code,
        )
        self.city2 = baker.make("City")

    def test_needs_city_code(self):
        make_service(is_draft=False, diffusion_zone_type=AdminDivisionType.COUNTRY)
        response = self.client.get("/search/")
        self.assertEqual(response.status_code, 404)

    def test_can_see_published_services(self):
        service = make_service(
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
        )
        response = self.client.get(f"/search/?city={self.city1.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service.slug)

    def test_cant_see_draft_services(self):
        make_service(is_draft=True, diffusion_zone_type=AdminDivisionType.COUNTRY)
        response = self.client.get(f"/search/?city={self.city1.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_cant_see_suggested_services(self):
        # En théorie, on ne peut pas avoir un service avec is_draft False et is_suggestion True
        # mais vérifions quand même qu'ils sont exclus des resultats de recherche
        make_service(
            is_draft=False,
            is_suggestion=True,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
        )
        response = self.client.get(f"/search/?city={self.city1.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_can_see_service_with_future_suspension_date(self):
        service = make_service(
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            suspension_date=timezone.now() + timedelta(days=1),
        )
        response = self.client.get(f"/search/?city={self.city1.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service.slug)

    def test_cannot_see_service_with_past_suspension_date(self):
        make_service(
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            suspension_date=timezone.now() - timedelta(days=1),
        )
        response = self.client.get(f"/search/?city={self.city1.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_find_services_in_city(self):
        service = make_service(
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.CITY,
            diffusion_zone_details=self.city1.code,
        )
        response = self.client.get(f"/search/?city={self.city1.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service.slug)

    def test_find_services_in_epci(self):
        service = make_service(
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.EPCI,
            diffusion_zone_details=self.epci11.code,
        )
        response = self.client.get(f"/search/?city={self.city1.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service.slug)

    def test_find_services_in_dept(self):
        service = make_service(
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.DEPARTMENT,
            diffusion_zone_details=self.dept.code,
        )
        response = self.client.get(f"/search/?city={self.city1.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service.slug)

    def test_find_services_in_region(self):
        service = make_service(
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.REGION,
            diffusion_zone_details=self.region.code,
        )
        response = self.client.get(f"/search/?city={self.city1.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service.slug)

    def test_dont_find_services_in_other_city(self):
        make_service(
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.CITY,
            diffusion_zone_details=self.city1.code,
        )
        response = self.client.get(f"/search/?city={self.city2.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_dont_find_services_in_other_epci(self):
        make_service(
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.EPCI,
            diffusion_zone_details=self.epci11.code,
        )
        response = self.client.get(f"/search/?city={self.city2.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_dont_find_services_in_other_department(self):
        make_service(
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.DEPARTMENT,
            diffusion_zone_details=self.dept.code,
        )
        response = self.client.get(f"/search/?city={self.city2.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_dont_find_services_in_other_region(self):
        make_service(
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.REGION,
            diffusion_zone_details=self.region.code,
        )
        response = self.client.get(f"/search/?city={self.city2.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_filter_by_fee_true(self):
        service1 = make_service(
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            has_fee=True,
        )
        make_service(
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            has_fee=False,
        )
        response = self.client.get(f"/search/?city={self.city1.code}&has_fee=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service1.slug)

    def test_filter_by_fee_false(self):
        make_service(
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            has_fee=True,
        )
        service2 = make_service(
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            has_fee=False,
        )
        response = self.client.get(f"/search/?city={self.city1.code}&has_fee=0")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service2.slug)

    def test_filter_without_fee(self):
        make_service(
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            has_fee=True,
        )
        make_service(
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            has_fee=False,
        )
        response = self.client.get(f"/search/?city={self.city1.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_filter_kinds_one(self):
        allowed_kinds = ServiceKind.objects.all()
        service1 = make_service(
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            kinds=[allowed_kinds[0], allowed_kinds[1]],
        )
        make_service(
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            kinds=[allowed_kinds[2]],
        )
        response = self.client.get(
            f"/search/?city={self.city1.code}&kinds={allowed_kinds[0].value}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service1.slug)

    def test_filter_kinds_several(self):
        allowed_kinds = ServiceKind.objects.all()
        service1 = make_service(
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            kinds=[allowed_kinds[0], allowed_kinds[1]],
        )
        service2 = make_service(
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            kinds=[allowed_kinds[1], allowed_kinds[2]],
        )
        make_service(
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            kinds=[allowed_kinds[3]],
        )
        response = self.client.get(
            f"/search/?city={self.city1.code}&kinds={allowed_kinds[1].value},{allowed_kinds[2].value}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        response_slugs = [r["slug"] for r in response.data]
        self.assertIn(service1.slug, response_slugs)
        self.assertIn(service2.slug, response_slugs)

    def test_filter_kinds_nomatch(self):
        allowed_kinds = ServiceKind.objects.all()
        make_service(
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            kinds=[allowed_kinds[0], allowed_kinds[1]],
        )
        make_service(
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            kinds=[allowed_kinds[1], allowed_kinds[2]],
        )
        response = self.client.get(
            f"/search/?city={self.city1.code}&kinds={allowed_kinds[3].value}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)


class ServiceSearchOrderingTestCase(APITestCase):
    def setUp(self):
        self.toulouse_center = Point(1.4436700, 43.6042600, srid=4326)
        self.blagnac_center = Point(1.3939900, 43.6327600, srid=4326)
        self.point_in_toulouse = Point(
            1.4187594455116272, 43.601528176416416, srid=4326
        )

        region = baker.make("Region", code="76")
        dept = baker.make("Department", region=region.code, code="31")
        toulouse = baker.make(
            "City",
            code="31555",
            department=dept.code,
            region=region.code,
            # la valeur du buffer est complètement approximative
            # elle permet juste de valider les assertions suivantes
            geom=MultiPolygon(self.toulouse_center.buffer(0.05)),
        )
        self.assertTrue(toulouse.geom.contains(self.toulouse_center))
        self.assertTrue(toulouse.geom.contains(self.point_in_toulouse))
        self.assertFalse(toulouse.geom.contains(self.blagnac_center))

    def test_on_site_first(self):
        self.assertEqual(Service.objects.all().count(), 0)
        service1 = make_service(
            slug="s1",
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.CITY,
            diffusion_zone_details="31555",
        )
        service1.location_kinds.set([LocationKind.objects.get(value="en-presentiel")])
        service2 = make_service(
            slug="s2",
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.CITY,
            diffusion_zone_details="31555",
        )
        service2.location_kinds.set([LocationKind.objects.get(value="a-distance")])
        service2.save()

        service3 = make_service(
            slug="s3",
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.CITY,
            diffusion_zone_details="31555",
        )
        service3.location_kinds.set([LocationKind.objects.get(value="en-presentiel")])
        service3.save()

        response = self.client.get("/search/?city=31555")
        self.assertEqual(response.data[0]["slug"], service3.slug)
        self.assertEqual(response.data[1]["slug"], service1.slug)
        self.assertEqual(response.data[2]["slug"], service2.slug)

    def test_on_site_nearest_first(self):
        self.assertEqual(Service.objects.all().count(), 0)
        service1 = make_service(
            slug="s1",
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.DEPARTMENT,
            diffusion_zone_details="31",
            geom=self.point_in_toulouse,
        )
        service1.location_kinds.set([LocationKind.objects.get(value="en-presentiel")])

        service2 = make_service(
            slug="s2",
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.DEPARTMENT,
            diffusion_zone_details="31",
            geom=self.blagnac_center,
        )
        service2.location_kinds.set([LocationKind.objects.get(value="en-presentiel")])
        service2.save()

        service3 = make_service(
            slug="s3",
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.DEPARTMENT,
            diffusion_zone_details="31",
            geom=self.toulouse_center,
        )
        service3.location_kinds.set([LocationKind.objects.get(value="en-presentiel")])
        service3.save()

        response = self.client.get("/search/?city=31555")

        self.assertEqual(response.data[0]["slug"], service3.slug)
        self.assertEqual(response.data[1]["slug"], service1.slug)
        self.assertEqual(response.data[2]["slug"], service2.slug)

    def test_on_site_same_dist_smallest_diffusion_first(self):
        self.assertEqual(Service.objects.all().count(), 0)
        service1 = make_service(
            slug="s1",
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.DEPARTMENT,
            diffusion_zone_details="31",
            geom=self.toulouse_center,
        )
        service1.location_kinds.set([LocationKind.objects.get(value="en-presentiel")])

        service2 = make_service(
            slug="s2",
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.REGION,
            diffusion_zone_details="76",
            geom=self.toulouse_center,
        )
        service2.location_kinds.set([LocationKind.objects.get(value="en-presentiel")])
        service2.save()

        service3 = make_service(
            slug="s3",
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.CITY,
            diffusion_zone_details="31555",
            geom=self.toulouse_center,
        )
        service3.location_kinds.set([LocationKind.objects.get(value="en-presentiel")])
        service3.save()

        response = self.client.get("/search/?city=31555")
        self.assertEqual(response.data[0]["slug"], service3.slug)
        self.assertEqual(response.data[1]["slug"], service1.slug)
        self.assertEqual(response.data[2]["slug"], service2.slug)

    def test_remote_smallest_diffusion_first(self):
        self.assertEqual(Service.objects.all().count(), 0)
        service1 = make_service(
            slug="s1",
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.DEPARTMENT,
            diffusion_zone_details="31",
            geom=self.toulouse_center,
        )
        service1.location_kinds.set([LocationKind.objects.get(value="a-distance")])

        service2 = make_service(
            slug="s2",
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.REGION,
            diffusion_zone_details="76",
            geom=self.toulouse_center,
        )
        service2.location_kinds.set([LocationKind.objects.get(value="a-distance")])
        service2.save()

        service3 = make_service(
            slug="s3",
            is_draft=False,
            diffusion_zone_type=AdminDivisionType.CITY,
            diffusion_zone_details="31555",
            geom=self.toulouse_center,
        )
        service3.location_kinds.set([LocationKind.objects.get(value="a-distance")])
        service3.save()

        response = self.client.get("/search/?city=31555")
        self.assertEqual(response.data[0]["slug"], service3.slug)
        self.assertEqual(response.data[1]["slug"], service1.slug)
        self.assertEqual(response.data[2]["slug"], service2.slug)


class ServiceModelTestCase(APITestCase):
    def test_everybody_can_see_draft_models(self):
        service = make_service(is_draft=True, is_model=True)
        response = self.client.get("/services/")
        self.assertEqual(response.status_code, 200)
        services_ids = [s["slug"] for s in response.data]
        self.assertIn(service.slug, services_ids)

    def test_everybody_can_see_is_model_param(self):
        service = make_service(is_draft=True, is_model=True)
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_model"])

    def test_can_set_is_model_param(self):
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        service = make_service(is_model=False, structure=struct)
        self.client.force_authenticate(user=user)
        response = self.client.patch(f"/services/{service.slug}/", {"is_model": True})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_model"])

    def test_can_unset_is_model_param(self):
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        service = make_service(is_model=True, structure=struct)
        self.client.force_authenticate(user=user)
        response = self.client.patch(f"/services/{service.slug}/", {"is_model": False})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_model"])

    def test_superuser_can_set_is_model_param(self):
        superuser = baker.make("users.User", is_staff=True, is_valid=True)
        service = make_service(is_model=False)
        self.client.force_authenticate(user=superuser)
        response = self.client.patch(f"/services/{service.slug}/", {"is_model": True})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_model"])

    def test_superuser_can_unset_is_model_param(self):
        superuser = baker.make("users.User", is_staff=True, is_valid=True)
        service = make_service(is_model=True)
        self.client.force_authenticate(user=superuser)
        response = self.client.patch(f"/services/{service.slug}/", {"is_model": False})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_model"])

    def test_other_cant_set_is_model_param(self):
        user = baker.make("users.User", is_valid=True)
        service = make_service(is_model=False, is_draft=False)
        self.client.force_authenticate(user=user)
        response = self.client.patch(f"/services/{service.slug}/", {"is_model": True})
        self.assertEqual(response.status_code, 403)

    def test_other_cant_unset_is_model_param(self):
        user = baker.make("users.User", is_valid=True)
        service = make_service(is_model=True, is_draft=False)
        self.client.force_authenticate(user=user)
        response = self.client.patch(f"/services/{service.slug}/", {"is_model": False})
        self.assertEqual(response.status_code, 403)

    def test_anonymous_cant_set_is_model_param(self):
        service = make_service(is_model=False, is_draft=False)
        response = self.client.patch(f"/services/{service.slug}/", {"is_model": True})
        self.assertEqual(response.status_code, 401)

    def test_anonymous_cant_unset_is_model_param(self):
        service = make_service(is_model=True, is_draft=False)
        response = self.client.patch(f"/services/{service.slug}/", {"is_model": False})
        self.assertEqual(response.status_code, 401)


class ServiceDuplicationTestCase(APITestCase):
    def test_field_change_updates_checksum(self):
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        service = make_service(structure=struct)
        self.client.force_authenticate(user=user)

        for field in SYNC_FIELDS:
            initial_checksum = service.sync_checksum
            if isinstance(getattr(service, field), bool):
                new_val = not getattr(service, field)
            elif field in ("online_form", "remote_url"):
                new_val = "https://example.com"
            elif field == "forms":
                new_val = ["https://example.com"]
            elif field == "contact_email":
                new_val = "test@example.com"
            elif field == "diffusion_zone_type":
                new_val = AdminDivisionType.REGION
            elif field == "suspension_date":
                new_val = "2022-10-10"
            elif field == "geom":
                continue
            else:
                new_val = "xxx"
            response = self.client.patch(f"/services/{service.slug}/", {field: new_val})
            self.assertEqual(response.status_code, 200, response.data)

            service.refresh_from_db()
            self.assertNotEqual(service.sync_checksum, initial_checksum)

    def test_other_field_change_doesnt_updates_checksum(self):
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        service = make_service(structure=struct)
        self.client.force_authenticate(user=user)

        initial_checksum = service.sync_checksum
        response = self.client.patch(
            f"/services/{service.slug}/", {"is_draft": not service.is_draft}
        )
        self.assertEqual(response.status_code, 200)
        service.refresh_from_db()
        self.assertEqual(service.sync_checksum, initial_checksum)

    def test_m2m_field_change_updates_checksum(self):
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        service = make_service(structure=struct)
        self.client.force_authenticate(user=user)

        for field in SYNC_M2M_FIELDS:
            initial_checksum = service.sync_checksum
            rel_model = getattr(service, field).target_field.related_model
            new_value = baker.make(rel_model)
            response = self.client.patch(
                f"/services/{service.slug}/", {field: [new_value.value]}
            )
            self.assertEqual(response.status_code, 200)
            service.refresh_from_db()
            self.assertNotEqual(service.sync_checksum, initial_checksum)

        for field in SYNC_CUSTOM_M2M_FIELDS:
            initial_checksum = service.sync_checksum
            rel_model = getattr(service, field).target_field.related_model
            new_value = baker.make(rel_model)
            response = self.client.patch(
                f"/services/{service.slug}/", {field: [new_value.id]}
            )
            self.assertEqual(response.status_code, 200)
            service.refresh_from_db()
            self.assertNotEqual(service.sync_checksum, initial_checksum)

    def test_copy_preserve_expected_fields(self):
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        service = make_service(structure=struct)

        for field in SYNC_M2M_FIELDS:
            rel_model = getattr(service, field).target_field.related_model
            new_value = baker.make(rel_model)
            getattr(service, field).set([new_value])

        for field in SYNC_CUSTOM_M2M_FIELDS:
            rel_model = getattr(service, field).target_field.related_model
            new_value = baker.make(rel_model)
            getattr(service, field).set([new_value])

        dest_struct = make_structure(user)

        self.client.force_authenticate(user=user)
        response = self.client.post(
            f"/services/{service.slug}/copy/", {"structure": dest_struct.slug}
        )
        self.assertEqual(response.status_code, 200)
        copy = Service.objects.get(slug=response.data["slug"])
        for field in SYNC_FIELDS:
            if field not in [
                "address1",
                "address2",
                "postal_code",
                "city_code",
                "city",
                "longitude",
                "latitude",
                "geom",
            ]:
                self.assertEqual(getattr(service, field), getattr(copy, field), field)
        for field in [*SYNC_M2M_FIELDS, *SYNC_CUSTOM_M2M_FIELDS]:
            self.assertQuerysetEqual(
                getattr(service, field).all(), getattr(copy, field).all()
            )

    def test_copy_change_variable_fields(self):
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        service = make_service(structure=struct)
        location = baker.make("LocationKind")
        service.location_kinds.set([location.id])
        dest_struct = make_structure(user)

        self.client.force_authenticate(user=user)
        response = self.client.post(
            f"/services/{service.slug}/copy/", {"structure": dest_struct.slug}
        )
        self.assertEqual(response.status_code, 200)
        copy = Service.objects.get(slug=response.data["slug"])

        self.assertEqual(copy.address1, dest_struct.address1)
        self.assertEqual(copy.address2, dest_struct.address2)
        self.assertEqual(copy.postal_code, dest_struct.postal_code)
        self.assertEqual(copy.city_code, dest_struct.city_code)
        self.assertEqual(copy.city, dest_struct.city)
        self.assertEqual(copy.geom.x, dest_struct.longitude)
        self.assertEqual(copy.geom.y, dest_struct.latitude)

    def test_copy_check_metadata(self):
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        service = make_service(structure=struct)
        dest_struct = make_structure(user)

        self.client.force_authenticate(user=user)
        response = self.client.post(
            f"/services/{service.slug}/copy/", {"structure": dest_struct.slug}
        )
        self.assertEqual(response.status_code, 200)
        copy = Service.objects.get(slug=response.data["slug"])
        self.assertTrue(copy.is_draft)
        self.assertFalse(copy.is_model)
        self.assertEqual(copy.creator, service.creator)
        self.assertEqual(copy.last_editor, user)
        self.assertEqual(copy.model, service)
        self.assertNotEqual(copy.creation_date, service.creation_date)
        self.assertNotEqual(copy.modification_date, service.modification_date)
        self.assertIsNone(copy.publication_date)


class ServiceDuplicationPermissionTestCase(APITestCase):
    def test_can_duplicate_my_services_in_my_structures(self):
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        service = make_service(structure=struct, is_model=False)
        dest_struct = make_structure(user)
        self.client.force_authenticate(user=user)
        response = self.client.post(
            f"/services/{service.slug}/copy/", {"structure": dest_struct.slug}
        )
        self.assertEqual(response.status_code, 200)

    def test_cant_duplicate_my_services_in_other_structures(self):
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        service = make_service(structure=struct, is_model=False)
        dest_struct = make_structure()
        self.client.force_authenticate(user=user)
        response = self.client.post(
            f"/services/{service.slug}/copy/", {"structure": dest_struct.slug}
        )
        self.assertEqual(response.status_code, 403)

    def test_cant_duplicate_other_draft_services_in_my_structures(self):
        user = baker.make("users.User", is_valid=True)
        service = make_service(is_model=False, is_draft=True)
        dest_struct = make_structure(user)
        self.client.force_authenticate(user=user)
        response = self.client.post(
            f"/services/{service.slug}/copy/", {"structure": dest_struct.slug}
        )
        self.assertEqual(response.status_code, 404)

    def test_cant_duplicate_other_services_in_my_structures(self):
        user = baker.make("users.User", is_valid=True)
        service = make_service(is_model=False, is_draft=False)
        dest_struct = make_structure(user)
        self.client.force_authenticate(user=user)
        response = self.client.post(
            f"/services/{service.slug}/copy/", {"structure": dest_struct.slug}
        )
        self.assertEqual(response.status_code, 403)

    def test_can_duplicate_models_in_my_structures(self):
        user = baker.make("users.User", is_valid=True)
        service = make_service(is_model=True, is_draft=False)
        dest_struct = make_structure(user)
        self.client.force_authenticate(user=user)
        response = self.client.post(
            f"/services/{service.slug}/copy/", {"structure": dest_struct.slug}
        )
        self.assertEqual(response.status_code, 200)

    def test_can_duplicate_draft_models_in_my_structures(self):
        user = baker.make("users.User", is_valid=True)
        service = make_service(is_model=True, is_draft=True)
        dest_struct = make_structure(user)
        self.client.force_authenticate(user=user)
        response = self.client.post(
            f"/services/{service.slug}/copy/", {"structure": dest_struct.slug}
        )
        self.assertEqual(response.status_code, 200)

    def test_cant_duplicate_models_in_other_structures(self):
        service = make_service(is_model=True, is_draft=False)
        dest_struct = make_structure()
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        response = self.client.post(
            f"/services/{service.slug}/copy/", {"structure": dest_struct.slug}
        )
        self.assertEqual(response.status_code, 403)


class ServiceSyncTestCase(APITestCase):
    def test_can_unsync_my_services(self):
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        source_service = make_service(structure=struct)
        dest_service = make_service(model=source_service, structure=struct)
        self.assertIsNotNone(dest_service.model)
        self.client.force_authenticate(user=user)
        response = self.client.post(f"/services/{dest_service.slug}/unsync/")
        self.assertEqual(response.status_code, 201)
        dest_service.refresh_from_db()
        self.assertIsNone(dest_service.model)

    def test_cant_unsync_a_service_not_synced(self):
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        dest_service = make_service(model=None, structure=struct)
        self.client.force_authenticate(user=user)
        response = self.client.post(f"/services/{dest_service.slug}/unsync/")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Ce service n'est pas synchronisé", repr(response.data))

    def test_cant_unsync_others_services(self):
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        source_service = make_service(
            structure=struct,
        )
        dest_service = make_service(model=source_service, is_draft=False)
        self.client.force_authenticate(user=user)
        response = self.client.post(f"/services/{dest_service.slug}/unsync/")
        self.assertEqual(response.status_code, 403)

    def test_cant_duplicate_a_duplicated_service(self):
        user = baker.make("users.User", is_valid=True)
        structure = make_structure(user)
        source = make_service(is_model=True)
        service = make_service(model=source, structure=structure)
        dest_struct = make_structure(user)
        self.client.force_authenticate(user=user)
        response = self.client.post(
            f"/services/{service.slug}/copy/", {"structure": dest_struct.slug}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Impossible de copier un service synchronisé", repr(response.data)
        )

    def test_can_sync_my_services(self):
        user = baker.make("users.User", is_valid=True)
        structure = make_structure(user)
        source = make_service(is_model=True, short_desc="yyy")
        service = make_service(model=source, structure=structure, short_desc="xxx")
        self.assertNotEqual(service.sync_checksum, source.sync_checksum)
        self.client.force_authenticate(user=user)
        response = self.client.post(
            f"/services/{service.slug}/sync/", {"fields": ["short_desc"]}
        )
        self.assertEqual(response.status_code, 200)
        source.refresh_from_db()
        service.refresh_from_db()
        self.assertEqual(service.short_desc, source.short_desc)

    def test_sync_updates_metadata(self):
        user = baker.make("users.User", is_valid=True)
        user2 = baker.make("users.User", is_valid=True)
        structure = make_structure(user)
        source = make_service(is_model=True, short_desc="yyy")
        service = make_service(
            model=source, structure=structure, short_desc="xxx", last_editor=user2
        )
        self.assertNotEqual(service.sync_checksum, source.sync_checksum)
        self.client.force_authenticate(user=user)
        response = self.client.post(
            f"/services/{service.slug}/sync/", {"fields": ["short_desc"]}
        )
        self.assertEqual(response.status_code, 200)
        service.refresh_from_db()
        self.assertEqual(service.last_editor, user)
        self.assertEqual(service.last_sync_checksum, source.sync_checksum)

    def test_sync_only_sync_requested_fields(self):
        user = baker.make("users.User", is_valid=True)
        structure = make_structure(user)
        source = make_service(is_model=True, short_desc="yyy", full_desc="abc")
        service = make_service(
            model=source, structure=structure, short_desc="xxx", full_desc="def"
        )
        self.client.force_authenticate(user=user)
        response = self.client.post(
            f"/services/{service.slug}/sync/", {"fields": ["short_desc"]}
        )
        self.assertEqual(response.status_code, 200)
        source.refresh_from_db()
        service.refresh_from_db()
        self.assertEqual(service.short_desc, source.short_desc)
        self.assertNotEqual(service.full_desc, source.full_desc)

    def test_cant_sync_uptodate_service(self):
        user = baker.make("users.User", is_valid=True)
        structure = make_structure(user)
        source = make_service(is_model=True, short_desc="yyy")
        service = copy_service(source, structure, user)
        self.client.force_authenticate(user=user)
        response = self.client.post(
            f"/services/{service.slug}/sync/", {"fields": ["short_desc"]}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Ce service est à jour", repr(response.data))

    def test_cant_sync_others_services(self):
        user = baker.make("users.User", is_valid=True)
        source = make_service(is_model=True)
        service = make_service(model=source, is_draft=False)
        self.client.force_authenticate(user=user)
        response = self.client.post(
            f"/services/{service.slug}/sync/", {"fields": ["short_desc"]}
        )
        self.assertEqual(response.status_code, 403)


class ServiceDiffTestCase(APITestCase):
    def test_cant_diff_others_services(self):
        user = baker.make("users.User", is_valid=True)
        user2 = baker.make("users.User", is_valid=True)
        structure = make_structure(user)
        source = make_service(is_model=True)
        service = copy_service(source, structure, user)
        source.short_desc = "xxx"
        source.save()
        service.is_draft = False
        service.save()
        self.client.force_authenticate(user=user2)
        response = self.client.get(
            f"/services/{service.slug}/diff/",
        )
        self.assertEqual(response.status_code, 403)

    def test_diffs_std_fields(self):
        user = baker.make("users.User", is_valid=True)
        structure = make_structure(user)
        source = make_service(is_model=True)
        service = copy_service(source, structure, user)
        source.short_desc = "xxx"
        source.save()
        self.client.force_authenticate(user=user)
        response = self.client.get(
            f"/services/{service.slug}/diff/",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["short_desc"]["parent"], source.short_desc)

    def test_diffs_M2M_fields(self):
        user = baker.make("users.User", is_valid=True)
        structure = make_structure(user)
        source = make_service(is_model=True)
        service = copy_service(source, structure, user)
        new_cat = baker.make(ServiceCategory)
        source.categories.set([new_cat])
        source.save()
        self.client.force_authenticate(user=user)
        response = self.client.get(
            f"/services/{service.slug}/diff/",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["categories"]["parent"][0]["value"],
            new_cat.value,
            response.data["categories"],
        )

    def test_diffs_M2M_custom_fields(self):
        user = baker.make("users.User", is_valid=True)
        structure = make_structure(user)
        source = make_service(is_model=True)
        service = copy_service(source, structure, user)
        new_ac = baker.make(AccessCondition)
        source.access_conditions.set([new_ac])
        source.save()
        self.client.force_authenticate(user=user)
        response = self.client.get(
            f"/services/{service.slug}/diff/",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["access_conditions"]["parent"][0]["value"],
            new_ac.pk,
            response.data["access_conditions"],
        )
