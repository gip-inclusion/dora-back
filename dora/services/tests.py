from datetime import timedelta

from django.contrib.gis.geos import MultiPolygon, Point
from django.core.exceptions import ValidationError
from django.utils import timezone
from model_bakery import baker
from rest_framework.test import APITestCase

from dora.admin_express.models import AdminDivisionType
from dora.core.test_utils import make_model, make_service, make_structure
from dora.services.enums import ServiceStatus
from dora.services.migration_utils import (
    add_categories_and_subcategories_if_subcategory,
    create_category,
    create_subcategory,
    delete_category,
    delete_subcategory,
    get_category_by_value,
    get_subcategory_by_value,
    replace_subcategory,
    unlink_services_from_category,
    unlink_services_from_subcategory,
    update_subcategory_value_and_label,
)
from dora.services.utils import SYNC_CUSTOM_M2M_FIELDS, SYNC_FIELDS, SYNC_M2M_FIELDS
from dora.structures.models import Structure

from .models import (
    AccessCondition,
    LocationKind,
    Service,
    ServiceCategory,
    ServiceKind,
    ServiceModel,
    ServiceModificationHistoryItem,
    ServiceStatusHistoryItem,
    ServiceSubCategory,
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
            structure=self.my_struct, status=ServiceStatus.PUBLISHED, creator=self.me
        )
        self.my_draft_service = make_service(
            structure=self.my_struct, status=ServiceStatus.DRAFT, creator=self.me
        )
        self.my_latest_draft_service = make_service(
            structure=self.my_struct, status=ServiceStatus.DRAFT, creator=self.me
        )

        self.other_service = make_service(status=ServiceStatus.PUBLISHED)
        self.other_draft_service = make_service(status=ServiceStatus.DRAFT)

        self.colleague_service = make_service(
            structure=self.my_struct, status=ServiceStatus.PUBLISHED
        )
        self.colleague_draft_service = make_service(
            structure=self.my_struct, status=ServiceStatus.DRAFT
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
            status=ServiceStatus.DRAFT,
        )
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 404)

    def test_cant_see_draft_if_not_accepted_by_admin(self):
        self.client.force_authenticate(user=self.unaccepted_user)
        service = make_service(
            structure=self.my_struct,
            status=ServiceStatus.DRAFT,
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
            structure=self.my_struct, status=ServiceStatus.DRAFT, creator=self.me
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
        service = make_service(status=ServiceStatus.DRAFT, creator=self.superuser)
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
            status=ServiceStatus.PUBLISHED,
            contact_name="FOO",
            contact_phone="1234",
            contact_email="foo@bar.buz",
            is_contact_info_public=True,
        )
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["contact_name"], "FOO")
        self.assertEqual(response.data["contact_phone"], "1234")
        self.assertEqual(response.data["contact_email"], "foo@bar.buz")

    def test_anonymous_user_cant_see_private_contact_info(self):
        self.client.force_authenticate(user=None)
        service = make_service(
            status=ServiceStatus.PUBLISHED,
            contact_name="FOO",
            contact_phone="1234",
            contact_email="foo@bar.buz",
            is_contact_info_public=False,
        )
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["contact_name"], "")
        self.assertEqual(response.data["contact_phone"], "")
        self.assertEqual(response.data["contact_email"], "")

    def test_logged_user_can_see_public_contact_info(self):
        service = make_service(
            status=ServiceStatus.PUBLISHED,
            contact_name="FOO",
            contact_phone="1234",
            contact_email="foo@bar.buz",
            is_contact_info_public=True,
        )
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["contact_name"], "FOO")
        self.assertEqual(response.data["contact_phone"], "1234")
        self.assertEqual(response.data["contact_email"], "foo@bar.buz")

    def test_logged_user_can_see_public_contact_info_if_not_accepted_by_admin(self):
        self.client.force_authenticate(user=self.unaccepted_user)
        service = make_service(
            status=ServiceStatus.PUBLISHED,
            contact_name="FOO",
            contact_phone="1234",
            contact_email="foo@bar.buz",
            is_contact_info_public=True,
        )
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["contact_name"], "FOO")
        self.assertEqual(response.data["contact_phone"], "1234")
        self.assertEqual(response.data["contact_email"], "foo@bar.buz")

    def test_logged_user_can_see_private_contact_info(self):
        service = make_service(
            status=ServiceStatus.PUBLISHED,
            contact_name="FOO",
            contact_phone="1234",
            contact_email="foo@bar.buz",
            is_contact_info_public=False,
        )
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["contact_name"], "FOO")
        self.assertEqual(response.data["contact_phone"], "1234")
        self.assertEqual(response.data["contact_email"], "foo@bar.buz")

    def test_logged_user_with_no_structure_cant_see_private_contact_info(self):
        user = baker.make("users.User", is_valid=True)
        service = make_service(
            status=ServiceStatus.PUBLISHED,
            contact_name="FOO",
            contact_phone="1234",
            contact_email="foo@bar.buz",
            is_contact_info_public=False,
        )
        self.client.force_authenticate(user=user)
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["contact_name"], "")
        self.assertEqual(response.data["contact_phone"], "")
        self.assertEqual(response.data["contact_email"], "")

    def test_nonvalidated_user_cant_see_private_contact_info(self):
        self.me.is_valid = False
        service = make_service(
            status=ServiceStatus.PUBLISHED,
            contact_name="FOO",
            contact_phone="1234",
            contact_email="foo@bar.buz",
            is_contact_info_public=False,
        )
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["contact_name"], "")
        self.assertEqual(response.data["contact_phone"], "")
        self.assertEqual(response.data["contact_email"], "")

    def test_logged_user_cant_see_public_contact_info_if_not_accepted_by_admin(self):
        self.client.force_authenticate(user=self.unaccepted_user)
        service = make_service(
            status=ServiceStatus.PUBLISHED,
            contact_name="FOO",
            contact_phone="1234",
            contact_email="foo@bar.buz",
            is_contact_info_public=False,
        )
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["contact_name"], "")
        self.assertEqual(response.data["contact_phone"], "")
        self.assertEqual(response.data["contact_email"], "")

    def test_direct_publishing_updates_publication_date(self):
        response = self.client.post(
            "/services/",
            {
                **DUMMY_SERVICE,
                "status": ServiceStatus.PUBLISHED,
                "structure": self.my_struct.slug,
            },
        )
        self.assertEqual(response.status_code, 201)
        service = Service.objects.get(slug=response.data["slug"])
        self.assertEqual(service.status, ServiceStatus.PUBLISHED)
        self.assertIsNotNone(service.publication_date)
        self.assertTrue(
            timezone.now() - service.publication_date < timedelta(seconds=1)
        )

    def test_publishing_from_draft_updates_publication_date(self):
        service = make_service(status=ServiceStatus.DRAFT, structure=self.my_struct)
        self.assertIsNone(service.publication_date)
        response = self.client.patch(
            f"/services/{service.slug}/", {"status": ServiceStatus.PUBLISHED}
        )
        self.assertEqual(response.status_code, 200)
        service.refresh_from_db()
        self.assertEqual(service.status, ServiceStatus.PUBLISHED)
        self.assertIsNotNone(service.publication_date)
        self.assertTrue(
            timezone.now() - service.publication_date < timedelta(seconds=1)
        )

    def test_updating_without_publishing_doesnt_update_publication_date(self):
        service = make_service(status=ServiceStatus.DRAFT, structure=self.my_struct)
        self.assertIsNone(service.publication_date)
        response = self.client.patch(f"/services/{service.slug}/", {"name": "xxx"})
        self.assertEqual(response.status_code, 200)
        service.refresh_from_db()
        self.assertEqual(service.status, ServiceStatus.DRAFT)
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
        self.assertFalse(ServiceModificationHistoryItem.objects.exists())
        self.client.patch(
            f"/services/{self.my_service.slug}/", {"name": "xxx", "address1": "yyy"}
        )
        hitem = ServiceModificationHistoryItem.objects.all()[0]
        self.assertEqual(hitem.fields, ["name", "address1"])

    def test_editing_log_m2m_change(self):
        self.assertFalse(ServiceModificationHistoryItem.objects.exists())
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

    def test_creating_draft_does_log_changes(self):
        DUMMY_SERVICE["structure"] = self.my_struct.slug
        self.assertFalse(ServiceModificationHistoryItem.objects.exists())
        response = self.client.post(
            "/services/",
            DUMMY_SERVICE,
        )
        self.assertEqual(response.status_code, 201)
        self.assertFalse(ServiceModificationHistoryItem.objects.exists())

    def test_editing_does_log_draft_changes(self):
        self.assertFalse(ServiceModificationHistoryItem.objects.exists())
        response = self.client.patch(
            f"/services/{self.my_draft_service.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ServiceModificationHistoryItem.objects.exists())

    def test_editing_log_current_status(self):
        self.assertFalse(ServiceModificationHistoryItem.objects.exists())
        response = self.client.patch(
            f"/services/{self.my_service.slug}/", {"name": "xxx", "status": "DRAFT"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ServiceModificationHistoryItem.objects.exists())
        hitem = ServiceModificationHistoryItem.objects.all()[0]
        self.assertEqual(hitem.user, self.me)
        self.assertEqual(hitem.status, ServiceStatus.DRAFT)
        self.assertEqual(hitem.service, self.my_service)
        self.assertEqual(hitem.fields, ["name", "status"])

    # Services count
    def test_members_see_all_services_count(self):
        user = baker.make("users.User", is_valid=True)
        structure = make_structure(user)
        service = make_service(status=ServiceStatus.PUBLISHED, structure=structure)
        make_service(status=ServiceStatus.PUBLISHED, structure=structure)
        make_service(status=ServiceStatus.DRAFT, structure=structure)
        self.client.force_authenticate(user=user)
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["structure_info"]["num_services"], 3)

    def test_su_see_all_services_count(self):
        user = baker.make("users.User", is_valid=True)
        structure = make_structure(user)
        service = make_service(status=ServiceStatus.PUBLISHED, structure=structure)
        make_service(status=ServiceStatus.PUBLISHED, structure=structure)
        make_service(status=ServiceStatus.DRAFT, structure=structure)
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["structure_info"]["num_services"], 3)

    def test_others_see_public_services_count(self):
        user = baker.make("users.User", is_valid=True)
        user2 = baker.make("users.User", is_valid=True)
        structure = make_structure(user)
        service = make_service(status=ServiceStatus.PUBLISHED, structure=structure)
        make_service(status=ServiceStatus.PUBLISHED, structure=structure)
        make_service(status=ServiceStatus.DRAFT, structure=structure)
        self.client.force_authenticate(user=user2)
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["structure_info"]["num_services"], 2)

    def test_anon_see_public_services_count(self):
        user = baker.make("users.User", is_valid=True)
        structure = make_structure(user)
        service = make_service(status=ServiceStatus.PUBLISHED, structure=structure)
        make_service(status=ServiceStatus.PUBLISHED, structure=structure)
        make_service(status=ServiceStatus.DRAFT, structure=structure)
        self.client.force_authenticate(None)
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["structure_info"]["num_services"], 2)

    # Test has_already_been_unpublished
    def test_has_already_been_unpublished_no_history(self):
        # ÉTANT DONNÉ un service sans historique de changement
        user = baker.make("users.User", is_valid=True)
        structure = make_structure(user)
        service = make_service(status=ServiceStatus.PUBLISHED, structure=structure)

        # QUAND on récupère ce service
        response = self.client.get(f"/services/{service.slug}/")

        # ALORS il est considéré comme n'ayant jamais été dépublié
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["has_already_been_unpublished"], False)

    def test_has_already_been_unpublished_without_published_in_history(self):
        # ÉTANT DONNÉ un service qui n'a jamais été dépublié
        user = baker.make("users.User", is_valid=True)
        structure = make_structure(user)
        service = make_service(status=ServiceStatus.PUBLISHED, structure=structure)

        baker.make(
            ServiceStatusHistoryItem,
            service=service,
            previous_status=ServiceStatus.DRAFT,
            new_status=ServiceStatus.PUBLISHED,
        )

        # QUAND on récupère ce service
        response = self.client.get(f"/services/{service.slug}/")

        # ALORS il est considéré comme n'ayant jamais été dépublié
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["has_already_been_unpublished"], False)

    def test_has_already_been_unpublished_with_published_in_history(self):
        # ÉTANT DONNÉ un service qui a été publié par le passé
        user = baker.make("users.User", is_valid=True)
        structure = make_structure(user)
        service = make_service(status=ServiceStatus.PUBLISHED, structure=structure)

        baker.make(
            ServiceStatusHistoryItem,
            service=service,
            previous_status=ServiceStatus.DRAFT,
            new_status=ServiceStatus.PUBLISHED,
        )
        baker.make(
            ServiceStatusHistoryItem,
            service=service,
            previous_status=ServiceStatus.PUBLISHED,
            new_status=ServiceStatus.DRAFT,
        )

        # QUAND on récupère ce service
        response = self.client.get(f"/services/{service.slug}/")

        # ALORS il est considéré comme ayant déjà été dépublié
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["has_already_been_unpublished"], True)


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
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
        )
        response = self.client.get("/search/")
        self.assertEqual(response.status_code, 404)

    def test_can_see_published_services(self):
        service = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
        )
        response = self.client.get(f"/search/?city={self.city1.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service.slug)

    def test_cant_see_draft_services(self):
        make_service(
            status=ServiceStatus.DRAFT, diffusion_zone_type=AdminDivisionType.COUNTRY
        )
        response = self.client.get(f"/search/?city={self.city1.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_cant_see_suggested_services(self):
        make_service(
            status=ServiceStatus.SUGGESTION,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
        )
        response = self.client.get(f"/search/?city={self.city1.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_can_see_service_with_future_suspension_date(self):
        service = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            suspension_date=timezone.now() + timedelta(days=1),
        )
        response = self.client.get(f"/search/?city={self.city1.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service.slug)

    def test_cannot_see_service_with_past_suspension_date(self):
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            suspension_date=timezone.now() - timedelta(days=1),
        )
        response = self.client.get(f"/search/?city={self.city1.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_find_services_in_city(self):
        service = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.CITY,
            diffusion_zone_details=self.city1.code,
        )
        response = self.client.get(f"/search/?city={self.city1.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service.slug)

    def test_find_services_in_epci(self):
        service = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.EPCI,
            diffusion_zone_details=self.epci11.code,
        )
        response = self.client.get(f"/search/?city={self.city1.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service.slug)

    def test_find_services_in_dept(self):
        service = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.DEPARTMENT,
            diffusion_zone_details=self.dept.code,
        )
        response = self.client.get(f"/search/?city={self.city1.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service.slug)

    def test_find_services_in_region(self):
        service = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.REGION,
            diffusion_zone_details=self.region.code,
        )
        response = self.client.get(f"/search/?city={self.city1.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service.slug)

    def test_dont_find_services_in_other_city(self):
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.CITY,
            diffusion_zone_details=self.city1.code,
        )
        response = self.client.get(f"/search/?city={self.city2.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_dont_find_services_in_other_epci(self):
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.EPCI,
            diffusion_zone_details=self.epci11.code,
        )
        response = self.client.get(f"/search/?city={self.city2.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_dont_find_services_in_other_department(self):
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.DEPARTMENT,
            diffusion_zone_details=self.dept.code,
        )
        response = self.client.get(f"/search/?city={self.city2.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_dont_find_services_in_other_region(self):
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.REGION,
            diffusion_zone_details=self.region.code,
        )
        response = self.client.get(f"/search/?city={self.city2.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_filter_by_fee_true(self):
        service1 = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            has_fee=True,
        )
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            has_fee=False,
        )
        response = self.client.get(f"/search/?city={self.city1.code}&has_fee=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service1.slug)

    def test_filter_by_fee_false(self):
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            has_fee=True,
        )
        service2 = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            has_fee=False,
        )
        response = self.client.get(f"/search/?city={self.city1.code}&has_fee=0")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service2.slug)

    def test_filter_without_fee(self):
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            has_fee=True,
        )
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            has_fee=False,
        )
        response = self.client.get(f"/search/?city={self.city1.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_filter_kinds_one(self):
        allowed_kinds = ServiceKind.objects.all()
        service1 = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            kinds=[allowed_kinds[0], allowed_kinds[1]],
        )
        make_service(
            status=ServiceStatus.PUBLISHED,
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
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            kinds=[allowed_kinds[0], allowed_kinds[1]],
        )
        service2 = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            kinds=[allowed_kinds[1], allowed_kinds[2]],
        )
        make_service(
            status=ServiceStatus.PUBLISHED,
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
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            kinds=[allowed_kinds[0], allowed_kinds[1]],
        )
        make_service(
            status=ServiceStatus.PUBLISHED,
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
        # Points à moins de 100km de Toulouse
        self.point_in_toulouse = Point(
            1.4187594455116272, 43.601528176416416, srid=4326
        )
        self.blagnac_center = Point(1.3939900, 43.6327600, srid=4326)
        self.montauban_center = Point(1.3573408017582829, 44.022187843162136, srid=4326)

        # Points à plus de 100km de Toulouse
        self.rocamadour_center = Point(1.6197328621667728, 44.79914551756315, srid=4326)
        self.paris_center = Point(2.349014, 48.864716, srid=4326)

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
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.CITY,
            diffusion_zone_details="31555",
            geom=self.point_in_toulouse,
        )
        service1.location_kinds.set([LocationKind.objects.get(value="en-presentiel")])
        service2 = make_service(
            slug="s2",
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.CITY,
            diffusion_zone_details="31555",
            geom=self.point_in_toulouse,
        )
        service2.location_kinds.set([LocationKind.objects.get(value="a-distance")])

        service3 = make_service(
            slug="s3",
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.CITY,
            diffusion_zone_details="31555",
            geom=self.point_in_toulouse,
        )
        service3.location_kinds.set([LocationKind.objects.get(value="en-presentiel")])

        response = self.client.get("/search/?city=31555")
        self.assertEqual(response.data[0]["slug"], service3.slug)
        self.assertEqual(response.data[1]["slug"], service1.slug)
        self.assertEqual(response.data[2]["slug"], service2.slug)

    def test_on_site_nearest_first(self):
        self.assertEqual(Service.objects.all().count(), 0)
        service1 = make_service(
            slug="s1",
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.DEPARTMENT,
            diffusion_zone_details="31",
            geom=self.point_in_toulouse,
        )
        service1.location_kinds.set([LocationKind.objects.get(value="en-presentiel")])

        service2 = make_service(
            slug="s2",
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.DEPARTMENT,
            diffusion_zone_details="31",
            geom=self.blagnac_center,
        )
        service2.location_kinds.set([LocationKind.objects.get(value="en-presentiel")])

        service3 = make_service(
            slug="s3",
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.DEPARTMENT,
            diffusion_zone_details="31",
            geom=self.toulouse_center,
        )
        service3.location_kinds.set([LocationKind.objects.get(value="en-presentiel")])

        response = self.client.get("/search/?city=31555")

        self.assertEqual(response.data[0]["slug"], service3.slug)
        self.assertEqual(response.data[1]["slug"], service1.slug)
        self.assertEqual(response.data[2]["slug"], service2.slug)

    def test_on_site_same_dist_smallest_diffusion_first(self):
        self.assertEqual(Service.objects.all().count(), 0)
        service1 = make_service(
            slug="s1",
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.DEPARTMENT,
            diffusion_zone_details="31",
            geom=self.toulouse_center,
        )
        service1.location_kinds.set([LocationKind.objects.get(value="en-presentiel")])

        service2 = make_service(
            slug="s2",
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.REGION,
            diffusion_zone_details="76",
            geom=self.toulouse_center,
        )
        service2.location_kinds.set([LocationKind.objects.get(value="en-presentiel")])

        service3 = make_service(
            slug="s3",
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.CITY,
            diffusion_zone_details="31555",
            geom=self.toulouse_center,
        )
        service3.location_kinds.set([LocationKind.objects.get(value="en-presentiel")])

        response = self.client.get("/search/?city=31555")
        self.assertEqual(response.data[0]["slug"], service3.slug)
        self.assertEqual(response.data[1]["slug"], service1.slug)
        self.assertEqual(response.data[2]["slug"], service2.slug)

    def test_remote_smallest_diffusion_first(self):
        self.assertEqual(Service.objects.all().count(), 0)
        service1 = make_service(
            slug="s1",
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.DEPARTMENT,
            diffusion_zone_details="31",
            geom=self.toulouse_center,
        )
        service1.location_kinds.set([LocationKind.objects.get(value="a-distance")])

        service2 = make_service(
            slug="s2",
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.REGION,
            diffusion_zone_details="76",
            geom=self.toulouse_center,
        )
        service2.location_kinds.set([LocationKind.objects.get(value="a-distance")])

        service3 = make_service(
            slug="s3",
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.CITY,
            diffusion_zone_details="31555",
            geom=self.toulouse_center,
        )
        service3.location_kinds.set([LocationKind.objects.get(value="a-distance")])

        response = self.client.get("/search/?city=31555")
        self.assertEqual(response.data[0]["slug"], service3.slug)
        self.assertEqual(response.data[1]["slug"], service1.slug)
        self.assertEqual(response.data[2]["slug"], service2.slug)

    def test_distance_is_correct(self):
        self.assertEqual(Service.objects.all().count(), 0)
        service1 = make_service(
            slug="s1",
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            geom=self.point_in_toulouse,
        )
        service1.location_kinds.set([LocationKind.objects.get(value="en-presentiel")])

        service2 = make_service(
            slug="s2",
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            geom=self.montauban_center,
        )
        service2.location_kinds.set([LocationKind.objects.get(value="en-presentiel")])

        response = self.client.get("/search/?city=31555")
        self.assertTrue(40 < response.data[1]["distance"] < 50)

    def test_distance_no_more_than_100km(self):
        self.assertEqual(Service.objects.all().count(), 0)
        service1 = make_service(
            slug="s1",
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            geom=self.point_in_toulouse,
        )
        service1.location_kinds.set([LocationKind.objects.get(value="en-presentiel")])

        service2 = make_service(
            slug="s2",
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            geom=self.rocamadour_center,
        )
        service2.location_kinds.set([LocationKind.objects.get(value="en-presentiel")])

        response = self.client.get("/search/?city=31555")
        self.assertEqual(len(response.data), 1)


class ServiceModelTestCase(APITestCase):
    def test_everybody_can_see_models(self):
        service = make_model()
        response = self.client.get("/models/")
        self.assertEqual(response.status_code, 200)
        services_ids = [s["slug"] for s in response.data]
        self.assertIn(service.slug, services_ids)

    def test_models_not_visible_in_service_lists(self):
        service = make_model()
        response = self.client.get("/services/")
        self.assertEqual(response.status_code, 200)
        services_ids = [s["slug"] for s in response.data]
        self.assertNotIn(service.slug, services_ids)

    def test_is_model_param_not_visible_in_services(self):
        service = make_service(status=ServiceStatus.PUBLISHED)
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("is_model", response.data)

    def test_cant_set_is_model_param_on_service(self):
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        service = make_service(structure=struct)
        self.client.force_authenticate(user=user)
        response = self.client.patch(f"/services/{service.slug}/", {"is_model": True})
        self.assertEqual(response.status_code, 200)
        service.refresh_from_db()
        self.assertFalse(service.is_model)

    def test_cant_unset_is_model_param_on_model(self):
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        model = make_model(structure=struct)
        self.client.force_authenticate(user=user)
        response = self.client.patch(f"/models/{model.slug}/", {"is_model": False})
        self.assertEqual(response.status_code, 200)
        model.refresh_from_db()
        self.assertTrue(model.is_model)

    def test_can_create_model_from_scratch(self):
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        self.client.force_authenticate(user=user)
        response = self.client.post(
            "/models/", {"structure": struct.slug, **DUMMY_SERVICE}
        )
        self.assertEqual(response.status_code, 201)
        slug = response.data["slug"]
        ServiceModel.objects.get(slug=slug)

    def test_can_create_model_from_my_service(self):
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        service = make_service(status=ServiceStatus.PUBLISHED, structure=struct)
        self.client.force_authenticate(user=user)
        response = self.client.post(
            "/models/",
            {"structure": struct.slug, "service": service.slug, **DUMMY_SERVICE},
        )
        self.assertEqual(response.status_code, 201)
        slug = response.data["slug"]
        service = ServiceModel.objects.get(slug=slug)
        self.assertEqual(service.structure.pk, struct.pk)

    def test_create_model_from_service_becomes_ancestor(self):
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        service = make_service(status=ServiceStatus.PUBLISHED, structure=struct)
        self.client.force_authenticate(user=user)
        response = self.client.post(
            "/models/",
            {"structure": struct.slug, "service": service.slug, **DUMMY_SERVICE},
        )
        self.assertEqual(response.status_code, 201)
        slug = response.data["slug"]
        model = ServiceModel.objects.get(slug=slug)
        self.assertEqual(model.structure.pk, struct.pk)
        service.refresh_from_db()
        self.assertEqual(service.model, model)
        self.assertEqual(service.last_sync_checksum, model.sync_checksum)

    def test_cant_create_model_from_others_service(self):
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        service = make_service(status=ServiceStatus.PUBLISHED)

        self.client.force_authenticate(user=user)
        response = self.client.post(
            "/models/",
            {"structure": struct.slug, "service": service.slug, **DUMMY_SERVICE},
        )
        self.assertEqual(response.status_code, 403)

    def test_can_create_service_from_any_model(self):
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        model = make_model(structure=struct)
        self.client.force_authenticate(user=user)
        response = self.client.post(
            "/services/",
            {"structure": struct.slug, "model": model.slug, **DUMMY_SERVICE},
        )
        self.assertEqual(response.status_code, 201)
        slug = response.data["slug"]
        service = Service.objects.get(slug=slug)
        self.assertEqual(service.structure.pk, struct.pk)
        self.assertEqual(service.model, model)
        self.assertEqual(service.last_sync_checksum, model.sync_checksum)

    def test_superuser_can_create_model_from_others_service(self):
        user = baker.make("users.User", is_valid=True, is_staff=True)
        struct = make_structure(user)
        service = make_service(status=ServiceStatus.PUBLISHED)
        self.client.force_authenticate(user=user)
        response = self.client.post(
            "/models/",
            {"structure": struct.slug, "service": service.slug, **DUMMY_SERVICE},
        )
        self.assertEqual(response.status_code, 201)

    # History logging
    def test_editing_log_change(self):
        self.assertFalse(ServiceModificationHistoryItem.objects.exists())
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        model = make_model(structure=struct)
        self.client.force_authenticate(user=user)
        response = self.client.patch(f"/models/{model.slug}/", {"name": "xxx"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ServiceModificationHistoryItem.objects.exists())
        hitem = ServiceModificationHistoryItem.objects.all()[0]
        self.assertEqual(hitem.user, user)
        self.assertEqual(hitem.service, model)
        self.assertEqual(hitem.fields, ["name"])
        self.assertTrue(timezone.now() - hitem.date < timedelta(seconds=1))

    def test_editing_log_multiple_change(self):
        self.assertFalse(ServiceModificationHistoryItem.objects.exists())
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        model = make_model(structure=struct)
        self.client.force_authenticate(user=user)
        self.client.patch(
            f"/models/{model.slug}/", {"name": "xxx", "short_desc": "yyy"}
        )
        hitem = ServiceModificationHistoryItem.objects.all()[0]
        self.assertEqual(hitem.fields, ["name", "short_desc"])

    def test_editing_log_m2m_change(self):
        self.assertFalse(ServiceModificationHistoryItem.objects.exists())
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        model = make_model(structure=struct)
        self.client.force_authenticate(user=user)
        response = self.client.patch(
            f"/models/{model.slug}/", {"access_conditions": ["xxx"]}
        )
        self.assertEqual(response.status_code, 200)
        hitem = ServiceModificationHistoryItem.objects.all()[0]
        self.assertEqual(
            hitem.fields,
            [
                "access_conditions",
            ],
        )

    def test_editing_doesnt_log_current_status(self):
        self.assertFalse(ServiceModificationHistoryItem.objects.exists())
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        model = make_model(structure=struct)
        self.assertFalse(ServiceModificationHistoryItem.objects.exists())
        self.client.force_authenticate(user=user)
        response = self.client.patch(
            f"/models/{model.slug}/", {"name": "xxx", "status": "DRAFT"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ServiceModificationHistoryItem.objects.exists())
        hitem = ServiceModificationHistoryItem.objects.all()[0]
        self.assertEqual(hitem.user, user)
        self.assertEqual(hitem.status, "")


class ServiceInstantiationTestCase(APITestCase):
    def test_cant_instantiate_a_service(self):
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        service = make_service(structure=struct, status=ServiceStatus.PUBLISHED)
        dest_struct = make_structure(user)
        self.client.force_authenticate(user=user)
        response = self.client.post(
            "/services/",
            {"structure": dest_struct.slug, "model": service.slug, **DUMMY_SERVICE},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual("does_not_exist", response.data["model"][0]["code"])

    def test_can_instantiate_models_in_my_structures(self):
        user = baker.make("users.User", is_valid=True)
        model = make_model()
        dest_struct = make_structure(user)
        self.client.force_authenticate(user=user)
        response = self.client.post(
            "/services/",
            {"structure": dest_struct.slug, "model": model.slug, **DUMMY_SERVICE},
        )

        self.assertEqual(response.status_code, 201)

    def test_cant_instantiate_models_in_other_structures(self):
        model = make_model()
        dest_struct = make_structure()
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        response = self.client.post(
            "/services/",
            {"structure": dest_struct.slug, "model": model.slug, **DUMMY_SERVICE},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual("not_member_of_struct", response.data["structure"][0]["code"])


class ServiceSyncTestCase(APITestCase):
    def test_can_unsync_my_services(self):
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        model = make_model(structure=struct)
        dest_service = make_service(
            model=model, structure=struct, status=ServiceStatus.PUBLISHED
        )
        self.assertIsNotNone(dest_service.model)
        self.client.force_authenticate(user=user)
        response = self.client.patch(f"/services/{dest_service.slug}/", {"model": None})
        self.assertEqual(response.status_code, 200)
        dest_service.refresh_from_db()
        self.assertIsNone(dest_service.model)

    def test_cant_unsync_others_services(self):
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)

        model = make_model(structure=struct)
        dest_service = make_service(model=model, status=ServiceStatus.PUBLISHED)
        self.client.force_authenticate(user=user)
        response = self.client.patch(f"/services/{dest_service.slug}/", {"model": None})
        self.assertEqual(response.status_code, 403)

    def test_field_change_updates_checksum(self):
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)

        model = make_model(structure=struct)
        self.client.force_authenticate(user=user)

        for field in SYNC_FIELDS:
            initial_checksum = model.sync_checksum
            if isinstance(getattr(model, field), bool):
                new_val = not getattr(model, field)
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
            response = self.client.patch(f"/models/{model.slug}/", {field: new_val})
            self.assertEqual(response.status_code, 200, response.data)

            model.refresh_from_db()
            self.assertNotEqual(model.sync_checksum, initial_checksum)

    def test_other_field_change_doesnt_updates_checksum(self):
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        model = make_model(structure=struct)
        self.client.force_authenticate(user=user)

        initial_checksum = model.sync_checksum
        response = self.client.patch(f"/models/{model.slug}/", {"address1": "xxx"})
        self.assertEqual(response.status_code, 200)

        model.refresh_from_db()
        self.assertEqual(model.sync_checksum, initial_checksum)

    def test_m2m_field_change_updates_checksum(self):
        user = baker.make("users.User", is_valid=True)
        struct = make_structure(user)
        model = make_model(structure=struct)
        self.client.force_authenticate(user=user)

        for field in SYNC_M2M_FIELDS:
            initial_checksum = model.sync_checksum
            rel_model = getattr(model, field).target_field.related_model
            new_value = baker.make(rel_model)
            response = self.client.patch(
                f"/models/{model.slug}/", {field: [new_value.value]}
            )
            self.assertEqual(response.status_code, 200)
            model.refresh_from_db()
            self.assertNotEqual(model.sync_checksum, initial_checksum)

        for field in SYNC_CUSTOM_M2M_FIELDS:
            initial_checksum = model.sync_checksum
            rel_model = getattr(model, field).target_field.related_model
            new_value = baker.make(rel_model)
            response = self.client.patch(
                f"/models/{model.slug}/", {field: [new_value.id]}
            )
            self.assertEqual(response.status_code, 200)
            model.refresh_from_db()
            self.assertNotEqual(model.sync_checksum, initial_checksum)


class ServiceArchiveTestCase(APITestCase):
    def setUp(self):
        self.me = baker.make("users.User", is_valid=True)
        self.superuser = baker.make("users.User", is_staff=True, is_valid=True)
        self.my_struct = make_structure(self.me)

    def test_can_archive_a_service(self):
        service = make_service(structure=self.my_struct, status=ServiceStatus.PUBLISHED)
        self.client.force_authenticate(user=self.me)

        response = self.client.patch(
            f"/services/{service.slug}/", {"status": "ARCHIVED"}
        )
        self.assertEqual(response.status_code, 200)
        service.refresh_from_db()
        self.assertEqual(service.status, ServiceStatus.ARCHIVED)

    def test_superuser_can_archive_others_services(self):
        service = make_service(status=ServiceStatus.PUBLISHED)
        self.client.force_authenticate(user=self.superuser)
        response = self.client.patch(
            f"/services/{service.slug}/", {"status": "ARCHIVED"}
        )
        self.assertEqual(response.status_code, 200)
        service.refresh_from_db()
        self.assertEqual(service.status, ServiceStatus.ARCHIVED)

    def test_cant_archive_others_services(self):
        service = make_service(status=ServiceStatus.PUBLISHED)
        self.client.force_authenticate(user=self.me)

        response = self.client.patch(
            f"/services/{service.slug}/", {"status": "ARCHIVED"}
        )
        self.assertEqual(response.status_code, 403)
        service.refresh_from_db()
        self.assertEqual(service.status, ServiceStatus.PUBLISHED)

    def test_anonymous_cant_archive_others_services(self):
        service = make_service(status=ServiceStatus.PUBLISHED)
        response = self.client.patch(
            f"/services/{service.slug}/", {"status": "ARCHIVED"}
        )
        self.assertEqual(response.status_code, 401)
        service.refresh_from_db()
        self.assertEqual(service.status, ServiceStatus.PUBLISHED)

    def test_can_unarchive_a_service(self):
        service = make_service(structure=self.my_struct, status=ServiceStatus.ARCHIVED)
        self.client.force_authenticate(user=self.me)

        response = self.client.patch(f"/services/{service.slug}/", {"status": "DRAFT"})
        self.assertEqual(response.status_code, 200)
        service.refresh_from_db()
        self.assertEqual(service.status, ServiceStatus.DRAFT)

    def test_cant_unarchive_others_services(self):
        service = make_service(status=ServiceStatus.ARCHIVED)
        self.client.force_authenticate(user=self.me)

        response = self.client.patch(f"/services/{service.slug}/", {"status": "DRAFT"})
        self.assertEqual(response.status_code, 404)
        service.refresh_from_db()
        self.assertEqual(service.status, ServiceStatus.ARCHIVED)

    def test_anonymous_cant_unarchive_others_services(self):
        service = make_service(status=ServiceStatus.ARCHIVED)
        response = self.client.patch(f"/services/{service.slug}/", {"status": "DRAFT"})
        self.assertEqual(response.status_code, 401)
        service.refresh_from_db()
        self.assertEqual(service.status, ServiceStatus.ARCHIVED)

    def test_superuser_can_unarchive_others_services(self):
        service = make_service(status=ServiceStatus.ARCHIVED)
        self.client.force_authenticate(user=self.superuser)
        response = self.client.patch(f"/services/{service.slug}/", {"status": "DRAFT"})
        self.assertEqual(response.status_code, 200)
        service.refresh_from_db()
        self.assertEqual(service.status, ServiceStatus.DRAFT)

    def test_can_see_my_archives(self):
        service = make_service(structure=self.my_struct, status=ServiceStatus.ARCHIVED)
        self.client.force_authenticate(user=self.me)
        response = self.client.get("/services/")
        services_ids = [s["slug"] for s in response.data]
        self.assertIn(service.slug, services_ids)

    def test_can_see_my_archived_services_in_structure(self):
        service = make_service(structure=self.my_struct, status=ServiceStatus.ARCHIVED)
        self.client.force_authenticate(user=self.me)
        response = self.client.get(f"/structures/{self.my_struct.slug}/")
        self.assertEqual(response.data["archived_services"][0]["slug"], service.slug)

    def test_dont_see_archive_by_default(self):
        make_service(structure=self.my_struct, status=ServiceStatus.ARCHIVED)
        self.client.force_authenticate(user=self.me)
        # TODO; pour l'instant l'endpoint /services/ récupère les archives…
        # response = self.client.get("/services/")
        # services_ids = [s["slug"] for s in response.data]
        # self.assertNotIn(service.slug, services_ids)

        response = self.client.get(f"/structures/{self.my_struct.slug}/")
        self.assertEqual(response.data["services"], [])

    def test_cant_see_others_archives(self):
        make_service(status=ServiceStatus.ARCHIVED)
        self.client.force_authenticate(user=self.me)
        response = self.client.get(f"/structures/{self.my_struct.slug}/")
        self.assertEqual(response.data["archived_services"], [])

    def test_anonymous_cant_see_any_archives(self):
        make_service(status=ServiceStatus.ARCHIVED)
        response = self.client.get(f"/structures/{self.my_struct.slug}/")
        self.assertEqual(response.data["archived_services"], [])

    def test_superuser_can_see_any_archives(self):
        service = make_service(status=ServiceStatus.ARCHIVED)
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(f"/structures/{service.structure.slug}/")
        self.assertEqual(response.data["archived_services"][0]["slug"], service.slug)

    def test_archives_dont_appear_in_search_results_anon(self):
        city = baker.make("City", code="12345")
        make_service(
            status=ServiceStatus.ARCHIVED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
        )
        response = self.client.get(f"/search/?city={city.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_archives_dont_appear_in_search_results_auth(self):
        city = baker.make("City", code="12345")
        make_service(
            status=ServiceStatus.ARCHIVED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
        )
        self.client.force_authenticate(user=self.me)
        response = self.client.get(f"/search/?city={city.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_archives_dont_appear_in_public_api_anon(self):
        make_service(status=ServiceStatus.ARCHIVED)
        response = self.client.get("/api/v1/services/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_archives_dont_appear_in_public_api_auth(self):
        make_service(status=ServiceStatus.ARCHIVED)
        self.client.force_authenticate(user=self.me)
        response = self.client.get("/api/v1/services/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)


class FillingServiceDurationTestCase(APITestCase):
    def test_add_draft_duration_on_create(self):
        duration_to_add = 30
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        dest_struct = make_structure(user)

        # QUAND on créait un service au status `brouillon`
        service_created = self.client.post(
            "/services/",
            {
                "structure": dest_struct.slug,
                "duration_to_add": duration_to_add,
                "status": ServiceStatus.DRAFT,
                **DUMMY_SERVICE,
            },
        )

        # ALORS on s'attend que la durée de contribution soit sauvegardée
        self.assertEqual(service_created.status_code, 201)
        response = self.client.get(f"/services/{service_created.data.get('slug')}/")
        self.assertEqual(duration_to_add, response.data.get("filling_duration"))

    def test_add_publish_service_duration_on_create(self):
        duration_to_add = 30
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        dest_struct = make_structure(user)

        # QUAND on créait un service au status `publié`
        service_created = self.client.post(
            "/services/",
            {
                "structure": dest_struct.slug,
                "duration_to_add": duration_to_add,
                "status": ServiceStatus.PUBLISHED,
                **DUMMY_SERVICE,
            },
        )

        # ALORS on s'attend que la durée de contribution soit sauvegardée
        self.assertEqual(service_created.status_code, 201)
        response = self.client.get(f"/services/{service_created.data.get('slug')}/")
        self.assertEqual(duration_to_add, response.data.get("filling_duration"))

    def test_add_draft_service_duration_on_update(self):
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        dest_struct = make_structure(user)

        # ÉTANT DONNÉ un service au status `brouillon` avec 20 secondes de temps de complétion
        service_created = self.client.post(
            "/services/",
            {
                "structure": dest_struct.slug,
                "duration_to_add": 20,
                "status": ServiceStatus.DRAFT,
                **DUMMY_SERVICE,
            },
        )

        # QUAND je le mets à jour avec une durée de complétion de 10
        self.client.patch(
            f"/services/{service_created.data.get('slug')}/",
            {
                "duration_to_add": 10,
            },
        )

        # ALORS on s'attend à une durée de complétion globale de 20+10=30
        response = self.client.get(f"/services/{service_created.data.get('slug')}/")
        self.assertEqual(20 + 10, response.data.get("filling_duration"))

    def test_publish_service_duration_on_update(self):
        # ÉTANT DONNÉ un service au statut `brouillon` avec 20 secondes de temps de complétion
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        dest_struct = make_structure(user)

        service_created = self.client.post(
            "/services/",
            {
                "structure": dest_struct.slug,
                "duration_to_add": 20,
                "status": ServiceStatus.DRAFT,
                **DUMMY_SERVICE,
            },
        )

        # QUAND ce service passe au statut `publié` avec un temps de complétion de 15 secondes
        self.client.patch(
            f"/services/{service_created.data.get('slug')}/",
            {
                "duration_to_add": 15,
                "status": ServiceStatus.PUBLISHED,
            },
        )

        # ALORS on s'attend à une durée de complétion globale de 20+15=35
        response = self.client.get(f"/services/{service_created.data.get('slug')}/")
        self.assertEqual(20 + 15, response.data.get("filling_duration"))

    def test__filling_duration_stays_the_same_when_updating_a_published_service(self):
        # ÉTANT DONNÉ un service au statut `publié` avec 20 secondes de temps de complétion
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        dest_struct = make_structure(user)

        service_created = self.client.post(
            "/services/",
            {
                "structure": dest_struct.slug,
                "duration_to_add": 20,
                "status": ServiceStatus.PUBLISHED,
                **DUMMY_SERVICE,
            },
        )

        # QUAND je met à jour ce service avec un temps de complétion de 20 secondes
        self.client.patch(
            f"/services/{service_created.data.get('slug')}/",
            {
                "duration_to_add": 20,
            },
        )

        # ALORS on s'attend à conserver le temps de complétion initial de 20 secondes
        response = self.client.get(f"/services/{service_created.data.get('slug')}/")
        self.assertEqual(20, response.data.get("filling_duration"))
        self.assertNotEquals(20 + 20, response.data.get("filling_duration"))

    def test__filling_duration_stays_the_same_when_updating_a_draft_service_already_published_in_the_past(
        self,
    ):
        # ÉTANT DONNÉ un service au statut `brouillon` avec 180 secondes de temps de complétion
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        structure = make_structure(user=user)
        service = make_service(
            structure=structure, filling_duration=180, status=ServiceStatus.DRAFT
        )
        service.refresh_from_db()

        # MAIS ayant déjà été publié dans le passé
        baker.make(
            ServiceStatusHistoryItem,
            service=service,
            new_status=ServiceStatus.PUBLISHED,
        )

        # QUAND je met à jour ce service avec un temps de complétion de 30 secondes
        self.client.patch(
            f"/services/{service.slug}/",
            {"duration_to_add": 30, "status": ServiceStatus.PUBLISHED},
        )

        # ALORS on s'attend à conserver le temps de complétion initial de 180 secondes
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(180, response.data.get("filling_duration"))
        self.assertNotEquals(180 + 30, response.data.get("filling_duration"))

    def test_filling_duration_stays_the_same_when_publishing_a_service_for_the_second_time(
        self,
    ):
        # ÉTANT DONNÉ un service au statut `brouillon` avec 180 secondes de temps de complétion
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        structure = make_structure(user=user)
        service = make_service(
            structure=structure, filling_duration=180, status=ServiceStatus.DRAFT
        )
        service.refresh_from_db()

        # MAIS ayant déjà été publié dans le passé
        baker.make(
            ServiceStatusHistoryItem,
            service=service,
            new_status=ServiceStatus.PUBLISHED,
        )

        # QUAND je publie ce service avec un temps de complétion de 30 secondes
        self.client.patch(
            f"/services/{service.slug}/",
            {"duration_to_add": 30, "status": ServiceStatus.PUBLISHED},
        )

        # ALORS on s'attend à conserver le temps de complétion initial de 180 secondes
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(180, response.data.get("filling_duration"))
        self.assertNotEquals(180 + 30, response.data.get("filling_duration"))


class ServiceStatusChangeTestCase(APITestCase):
    def setUp(self):
        self.user = baker.make("users.User", is_valid=True)
        self.struct = make_structure(self.user)
        self.client.force_authenticate(user=self.user)

    def test_changing_state_creates_history_item(self):
        service = make_service(structure=self.struct, status=ServiceStatus.DRAFT)
        self.assertEqual(
            ServiceStatusHistoryItem.objects.filter(service=service).count(), 0
        )
        response = self.client.patch(
            f"/services/{service.slug}/", {"status": "PUBLISHED"}
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            ServiceStatusHistoryItem.objects.filter(service=service).count(), 1
        )
        status_item = ServiceStatusHistoryItem.objects.get(service=service)
        self.assertEqual(status_item.new_status, "PUBLISHED")
        self.assertEqual(status_item.previous_status, "DRAFT")

    def test_history_item_logs_user(self):
        service = make_service(structure=self.struct, status=ServiceStatus.DRAFT)
        self.assertEqual(
            ServiceStatusHistoryItem.objects.filter(service=service).count(), 0
        )
        response = self.client.patch(
            f"/services/{service.slug}/", {"status": "PUBLISHED"}
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            ServiceStatusHistoryItem.objects.filter(service=service).count(), 1
        )
        status_item = ServiceStatusHistoryItem.objects.get(service=service)
        self.assertEqual(status_item.user, self.user)

    def test_get_previous_status_returns_correct_value(self):
        service = make_service(structure=self.struct, status=ServiceStatus.PUBLISHED)
        self.assertEqual(
            ServiceStatusHistoryItem.objects.filter(service=service).count(), 0
        )
        response = self.client.patch(
            f"/services/{service.slug}/", {"status": "ARCHIVED"}
        )
        self.assertEqual(response.status_code, 200)
        service.refresh_from_db()
        self.assertEqual(service.get_previous_status(), "PUBLISHED")
        response = self.client.patch(f"/services/{service.slug}/", {"status": "DRAFT"})
        self.assertEqual(response.status_code, 200)
        service.refresh_from_db()
        self.assertEqual(service.get_previous_status(), "ARCHIVED")
        self.assertEqual(
            ServiceStatusHistoryItem.objects.filter(service=service).count(), 2
        )


class ServiceMigrationUtilsTestCase(APITestCase):
    def test_delete_category(self):
        # ÉTANT DONNÉ une thématique
        value = "test-category"
        baker.make("ServiceCategory", value=value, label="Label_1")
        self.assertEqual(ServiceCategory.objects.filter(value=value).count(), 1)

        # QUAND je supprime cette thématique
        delete_category(ServiceCategory, value)

        # ALORS elle n'existe plus
        self.assertEqual(ServiceCategory.objects.filter(value=value).count(), 0)

    def test_delete_two_categories(self):
        # ÉTANT DONNÉ deux thématiques
        value = "test-category"
        baker.make("ServiceCategory", value=value, label="Label_1")

        value_2 = "test-category-2"
        baker.make("ServiceCategory", value=value_2, label="Label_2")
        self.assertEqual(
            ServiceCategory.objects.filter(value__in=[value, value_2]).count(), 2
        )

        # QUAND je supprime une thématique
        delete_category(ServiceCategory, value)

        # ALORS il en reste toujours une
        self.assertEqual(
            ServiceCategory.objects.filter(value__in=[value, value_2]).count(), 1
        )
        self.assertEqual(ServiceCategory.objects.filter(value=value_2).count(), 1)

    def test_delete_subcategory(self):
        # ÉTANT DONNÉ un besoin
        value = "test-subcategory"
        baker.make("ServiceSubCategory", value=value, label="Label_1")
        self.assertEqual(ServiceSubCategory.objects.filter(value=value).count(), 1)

        # QUAND je supprime ce besoin
        delete_subcategory(ServiceSubCategory, value)

        # ALORS il n'existe plus
        self.assertEqual(ServiceSubCategory.objects.filter(value=value).count(), 0)

    def test_delete_two_subcategories(self):
        # ÉTANT DONNÉ deux besoins
        value = "test-subcategory"
        baker.make("ServiceSubCategory", value=value, label="Label_1")

        value_2 = "test-subcategory-2"
        baker.make("ServiceSubCategory", value=value_2, label="Label_2")
        self.assertEqual(
            ServiceSubCategory.objects.filter(value__in=[value, value_2]).count(), 2
        )

        # QUAND je supprime ce besoin
        delete_subcategory(ServiceSubCategory, value)

        # ALORS il en reste toujours un
        self.assertEqual(
            ServiceSubCategory.objects.filter(value__in=[value, value_2]).count(), 1
        )
        self.assertEqual(ServiceSubCategory.objects.filter(value=value_2).count(), 1)

    def test_cant_replace_subcategory_by_nonexistent_subcategory(self):
        # ÉTANT DONNÉ une thématique existante et une thématique inexistante
        value = "subcategory_1"
        subcategory = baker.make("ServiceSubCategory", value=value)
        service = make_service()
        service.subcategories.add(subcategory)

        with self.assertRaises(ValidationError):
            replace_subcategory(
                ServiceSubCategory, Service, value, "non_existing_subcategory"
            )

    def test_replace_subcategory(self):
        # ÉTANT DONNÉ deux besoins
        subcategory_value_1 = "subcategory_1"
        subcategory_1 = baker.make("ServiceSubCategory", value=subcategory_value_1)
        service = make_service()
        service.subcategories.add(subcategory_1)

        subcategory_value_2 = "subcategory_2"
        baker.make("ServiceSubCategory", value=subcategory_value_2)

        service = Service.objects.filter(pk=service.pk).first()
        subcategories = service.subcategories.values_list("value", flat=True)
        self.assertTrue(subcategory_value_1 in subcategories)
        self.assertFalse(subcategory_value_2 in subcategories)

        # QUAND je remplace le besoin par le second
        replace_subcategory(
            ServiceSubCategory, Service, subcategory_value_1, subcategory_value_2
        )

        # ALORS le besoin a bien été remplacé
        service.refresh_from_db()
        subcategories = service.subcategories.values_list("value", flat=True)
        self.assertFalse(subcategory_value_1 in subcategories)
        self.assertTrue(subcategory_value_2 in subcategories)

    def test_create_category(self):
        # ÉTANT DONNÉ une thématique non existante
        value = "category_1"
        label = "label_category_1"
        self.assertEqual(ServiceCategory.objects.filter(value=value).count(), 0)

        # QUAND je créé cette catégorie
        create_category(ServiceCategory, value, label)

        # ALORS elle existe
        category = ServiceCategory.objects.filter(value=value)
        self.assertEqual(category.count(), 1)
        self.assertEqual(category.first().value, value)
        self.assertEqual(category.first().label, label)

    def test_create_subcategory(self):
        # ÉTANT DONNÉ un besoin non existant
        value = "subcategory_1"
        label = "label_subcategory_1"
        self.assertEqual(ServiceSubCategory.objects.filter(value=value).count(), 0)

        # QUAND je créé cette catégorie
        create_subcategory(ServiceSubCategory, value, label)

        # ALORS elle existe
        subcategory = ServiceSubCategory.objects.filter(value=value)
        self.assertEqual(subcategory.count(), 1)
        self.assertEqual(subcategory.first().value, value)
        self.assertEqual(subcategory.first().label, label)

    def test_get_category_by_value_None(self):
        # ÉTANT DONNÉ une thématique non existante
        # QUAND je récupère cette thématique
        subcategory = get_category_by_value(ServiceCategory, value="non_existing")

        # ALORS je récupère None
        self.assertEqual(subcategory, None)

    def test_get_category_by_value(self):
        # ÉTANT DONNÉ une thématique existante
        value = "value_category_1"
        label = "label_category_1"
        baker.make("ServiceCategory", value=value, label=label)

        # QUAND je récupère cette thématique
        category = get_category_by_value(ServiceCategory, value=value)

        # ALORS je récupère la bonne catégorie
        self.assertTrue(category is not None)
        self.assertEqual(category.value, value)
        self.assertEqual(category.label, label)

    def test_get_subcategory_by_value_None(self):
        # ÉTANT DONNÉ un besoin non existant
        # QUAND je récupère ce besoin
        category = get_subcategory_by_value(ServiceSubCategory, value="non_existing")

        # ALORS je récupère None
        self.assertEqual(category, None)

    def test_get_subcategory_by_value(self):
        # ÉTANT DONNÉ un besoin
        value = "value_subcategory_1"
        label = "label_subcategory_1"
        baker.make("ServiceSubCategory", value=value, label=label)

        # QUAND je récupère ce besoin
        subcategory = get_category_by_value(ServiceSubCategory, value=value)

        # ALORS je récupère le bon besoin
        self.assertTrue(subcategory is not None)
        self.assertEqual(subcategory.value, value)
        self.assertEqual(subcategory.label, label)

    def test_update_subcategory_value_and_label_non_existing(self):
        # ÉTANT DONNÉ un besoin non existant
        # QUAND je le modifie
        try:
            update_subcategory_value_and_label(
                ServiceSubCategory,
                old_value="value",
                new_value="whatever",
                new_label="new label",
            )
        except Exception as e:
            err = e

        # ALORS j'obtiens une erreur
        self.assertTrue(isinstance(err, ValidationError))
        self.assertTrue("Aucun besoin trouvé" in err.message)

    def test_update_subcategory_value_and_label_value_already_used(self):
        old_value = "old_value"
        new_value = "new_value"

        # ÉTANT DONNÉ un besoin existant
        baker.make("ServiceSubCategory", value=old_value, label="Label_1")
        # ET un besoin portant la future value
        baker.make("ServiceSubCategory", value=new_value, label="Label_2")

        # QUAND je le modifie
        try:
            update_subcategory_value_and_label(
                ServiceSubCategory,
                old_value=old_value,
                new_value=new_value,
                new_label="new label",
            )
        except Exception as e:
            err = e

        # ALORS j'obtiens une erreur
        self.assertTrue("est déjà utilisée" in err.message)

    def test_update_subcategory_value_and_label_value(self):
        old_value = "old_value"
        new_value = "new_value"
        new_label = "new_label"

        # ÉTANT DONNÉ un besoin existant
        baker.make("ServiceSubCategory", value=old_value, label="Label_1")
        self.assertEqual(ServiceSubCategory.objects.filter(value=old_value).count(), 1)

        # QUAND je le modifie
        update_subcategory_value_and_label(
            ServiceSubCategory,
            old_value=old_value,
            new_value=new_value,
            new_label=new_label,
        )

        # ALORS le besoin est correctement modifié
        self.assertEqual(ServiceSubCategory.objects.filter(value=old_value).count(), 0)

        subcategory = ServiceSubCategory.objects.filter(value=new_value)
        self.assertEqual(subcategory.count(), 1)
        self.assertEqual(subcategory.first().value, new_value)
        self.assertEqual(subcategory.first().label, new_label)

    def test_unlink_services_from_category(self):
        # ÉTANT DONNÉ un service existant lié à deux thématiques
        category_value_1 = "category_1"
        category_value_2 = "category_2"
        category_1 = baker.make("ServiceCategory", value=category_value_1)
        category_2 = baker.make("ServiceCategory", value=category_value_2)

        service = make_service()
        service.categories.add(category_1)
        service.categories.add(category_2)
        service.refresh_from_db()

        self.assertTrue(len(service.categories.values()), 2)

        # QUAND je retire une thématique
        unlink_services_from_category(
            ServiceCategory, Service, category_value=category_value_1
        )

        # ALORS le besoin est correctement modifié
        service.refresh_from_db()
        self.assertTrue(len(service.categories.values()), 1)
        self.assertEqual(service.categories.values()[0]["value"], category_value_2)

    def test_unlink_services_from_subcategory(self):
        # ÉTANT DONNÉ un service existant lié à deux besoins
        subcategory_value_1 = "subcategory_1"
        subcategory_value_2 = "subcategory_2"
        subcategory_1 = baker.make("ServiceSubCategory", value=subcategory_value_1)
        subcategory_2 = baker.make("ServiceSubCategory", value=subcategory_value_2)

        service = make_service()
        service.subcategories.add(subcategory_1)
        service.subcategories.add(subcategory_2)
        service.refresh_from_db()

        self.assertTrue(len(service.subcategories.values()), 2)

        # QUAND je retire un besoin
        unlink_services_from_subcategory(
            ServiceSubCategory, Service, subcategory_value=subcategory_value_1
        )

        # ALORS le besoin est correctement modifié
        service.refresh_from_db()
        self.assertTrue(len(service.subcategories.values()), 1)
        self.assertEqual(
            service.subcategories.values()[0]["value"], subcategory_value_2
        )

    def test_add_categories_and_subcategories_if_subcategory(self):
        # ÉTANT DONNÉ un service associé à un besoin "subcategory_1"
        subcategory_value_1 = "subcategory_1"
        subcategory_1 = baker.make("ServiceSubCategory", value=subcategory_value_1)
        service = make_service()
        service.subcategories.add(subcategory_1)

        # ET un service associé à un besoin "subcategory_2"
        subcategory_value_2 = "subcategory_2"
        subcategory_2 = baker.make("ServiceSubCategory", value=subcategory_value_2)
        service_2 = make_service()
        service_2.subcategories.add(subcategory_2)

        # ET 3 besoins et 1 thématique relié à aucun service
        subcategory_value_3 = "subcategory_3"
        subcategory_value_4 = "subcategory_4"
        subcategory_value_5 = "subcategory_5"
        baker.make("ServiceSubCategory", value=subcategory_value_3)
        baker.make("ServiceSubCategory", value=subcategory_value_4)
        baker.make("ServiceSubCategory", value=subcategory_value_5)

        category_value_1 = "category_1"
        baker.make("ServiceCategory", value=category_value_1)

        # QUAND j'ajoute les 3 besoins et 1 thématique s'ils ont déjà le besoin `subcategory_1`
        add_categories_and_subcategories_if_subcategory(
            ServiceCategory,
            ServiceSubCategory,
            Service,
            categories_value_to_add=[category_value_1],
            subcategory_value_to_add=[
                subcategory_value_3,
                subcategory_value_4,
                subcategory_value_5,
            ],
            if_subcategory_value=subcategory_value_1,
        )

        # ALORS le service est correctement modifié
        service.refresh_from_db()
        self.assertEqual(len(service.categories.values()), 1)
        self.assertEqual(service.categories.values()[0]["value"], category_value_1)

        self.assertEqual(len(service.subcategories.values()), 4)
        self.assertEqual(
            sorted(service.subcategories.values_list("value", flat=True)),
            sorted(
                [
                    subcategory_value_1,
                    subcategory_value_3,
                    subcategory_value_4,
                    subcategory_value_5,
                ]
            ),
        )

        # ET aucun changement pour le second service
        service_2.refresh_from_db()
        self.assertEqual(len(service_2.categories.values()), 0)
        self.assertEqual(len(service_2.subcategories.values()), 1)
        self.assertEqual(
            service_2.subcategories.values()[0]["value"], subcategory_value_2
        )

    def test_add_categories_and_no_subcategories_if_subcategory(self):
        # ÉTANT DONNÉ un service associé à un besoin "subcategory_1"
        subcategory_value_1 = "subcategory_1"
        subcategory_1 = baker.make("ServiceSubCategory", value=subcategory_value_1)
        service = make_service()
        service.subcategories.add(subcategory_1)

        # ET 1 thématique relié à aucun service
        category_value_1 = "category_1"
        baker.make("ServiceCategory", value=category_value_1)

        # QUAND 1 thématique et 0 besoins s'ils ont déjà le besoin `subcategory_1`
        add_categories_and_subcategories_if_subcategory(
            ServiceCategory,
            ServiceSubCategory,
            Service,
            categories_value_to_add=[category_value_1],
            subcategory_value_to_add=[],
            if_subcategory_value=subcategory_value_1,
        )

        # ALORS le service est correctement modifié
        service.refresh_from_db()
        self.assertEqual(len(service.categories.values()), 1)
        self.assertEqual(service.categories.values()[0]["value"], category_value_1)

        self.assertEqual(len(service.subcategories.values()), 1)
        self.assertEqual(
            sorted([s["value"] for s in service.subcategories.values()]),
            sorted([subcategory_value_1]),
        )
