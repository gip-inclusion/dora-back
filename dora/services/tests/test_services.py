from datetime import timedelta

import requests
from django.contrib.gis.geos import MultiPolygon, Point
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.utils import timezone
from model_bakery import baker
from rest_framework.test import APIRequestFactory, APITestCase

from dora.admin_express.models import AdminDivisionType
from dora.core.test_utils import make_model, make_service, make_structure
from dora.data_inclusion.test_utils import FakeDataInclusionClient, make_di_service_data
from dora.services.enums import ServiceStatus
from dora.services.migration_utils import (
    add_categories_and_subcategories_if_subcategory,
    create_category,
    create_service_kind,
    create_subcategory,
    delete_category,
    delete_subcategory,
    get_category_by_value,
    get_subcategory_by_value,
    rename_subcategory,
    replace_subcategory,
    unlink_services_from_category,
    unlink_services_from_subcategory,
    update_category_value_and_label,
    update_subcategory_value_and_label,
)
from dora.services.serializers import ServiceSerializer
from dora.structures.models import Structure

from ..models import (
    AccessCondition,
    BeneficiaryAccessMode,
    CoachOrientationMode,
    LocationKind,
    Service,
    ServiceCategory,
    ServiceFee,
    ServiceKind,
    ServiceModificationHistoryItem,
    ServiceStatusHistoryItem,
    ServiceSubCategory,
)
from ..utils import SYNC_CUSTOM_M2M_FIELDS, SYNC_FIELDS, SYNC_M2M_FIELDS
from ..views import search, service_di

DUMMY_SERVICE = {"name": "Mon service"}


class ServiceTestCase(APITestCase):
    def setUp(self):
        self.me = baker.make("users.User", is_valid=True)
        self.unaccepted_user = baker.make("users.User", is_valid=True)
        self.superuser = baker.make("users.User", is_staff=True, is_valid=True)
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

        self.manager = baker.make(
            "users.User", is_manager=True, is_valid=True, department="31"
        )
        self.struct_31 = make_structure(department="31")
        self.service_31 = make_service(
            structure=self.struct_31, status=ServiceStatus.PUBLISHED
        )
        self.draft_31 = make_service(
            structure=self.struct_31, status=ServiceStatus.DRAFT
        )

        self.struct_31_condition1 = baker.make(
            "AccessCondition", structure=self.struct_31
        )
        self.struct_31_condition2 = baker.make(
            "AccessCondition", structure=self.struct_31
        )

        self.struct_44 = make_structure(department="44")
        self.service_44 = make_service(
            structure=self.struct_44, status=ServiceStatus.PUBLISHED
        )
        self.draft_44 = make_service(
            structure=self.struct_44, status=ServiceStatus.DRAFT
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

    def test_update_fee_condition(self):
        slug = self.colleague_service.slug
        fee_condition = "gratuit"
        response = self.client.patch(
            f"/services/{slug}/",
            {"fee_condition": fee_condition},
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/services/{slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["fee_condition"], fee_condition)

    def test_update_fee_condition_error(self):
        slug = self.colleague_service.slug
        fee_condition = "xxx"
        response = self.client.patch(
            f"/services/{slug}/",
            {"fee_condition": fee_condition},
        )
        self.assertEqual(response.status_code, 400)

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

    # Superuser

    def test_superuser_can_sees_everything(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get("/services/")
        services_ids = [s["slug"] for s in response.data]
        self.assertIn(self.my_service.slug, services_ids)
        self.assertIn(self.my_draft_service.slug, services_ids)
        self.assertIn(self.other_service.slug, services_ids)
        self.assertIn(self.other_draft_service.slug, services_ids)

    def test_manager_can_sees_everything_in_its_department(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.get("/services/")
        services_ids = [s["slug"] for s in response.data]
        self.assertIn(self.service_31.slug, services_ids)
        self.assertIn(self.draft_31.slug, services_ids)

    def test_manager_can_sees_published_services_outside_its_department(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.get("/services/")
        services_ids = [s["slug"] for s in response.data]
        self.assertIn(self.service_44.slug, services_ids)
        self.assertIn(self.my_service.slug, services_ids)
        self.assertIn(self.other_service.slug, services_ids)

    def test_manager_cant_sees_drafts_outside_its_department(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.get("/services/")
        services_ids = [s["slug"] for s in response.data]
        self.assertNotIn(self.draft_44.slug, services_ids)
        self.assertNotIn(self.my_draft_service.slug, services_ids)
        self.assertNotIn(self.other_draft_service, services_ids)

    def test_manager_can_see_its_drafs_outside_its_department(self):
        self.client.force_authenticate(user=self.manager)
        struct_44 = make_structure(self.manager, department="44")
        draft_44 = make_service(structure=struct_44, status=ServiceStatus.DRAFT)

        response = self.client.get(f"/services/{draft_44.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], draft_44.name)

    def test_superuser_can_edit_everything(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.patch(
            f"/services/{self.my_draft_service.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/services/{self.my_draft_service.slug}/")
        self.assertEqual(response.data["name"], "xxx")

    def test_manager_can_edit_everything_inside_its_department(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(
            f"/services/{self.service_31.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/services/{self.service_31.slug}/")
        self.assertEqual(response.data["name"], "xxx")

        response = self.client.patch(
            f"/services/{self.draft_31.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/services/{self.draft_31.slug}/")
        self.assertEqual(response.data["name"], "xxx")

    def test_manager_cant_edit_outside_its_department(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(
            f"/services/{self.service_44.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_write_field_true(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(f"/services/{self.my_service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["can_write"], True)

    def test_manager_can_write_field_true_inside_its_department(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.get(f"/services/{self.service_31.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["can_write"], True)

    def test_manager_can_write_field_false_outside_its_department(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.get(f"/services/{self.service_44.slug}/")
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
        self.assertEqual(response.status_code, 403)

    def test_add_service_check_structure(self):
        DUMMY_SERVICE["structure"] = baker.make(
            "Structure", _fill_optional=["siret"]
        ).slug
        response = self.client.post(
            "/services/",
            DUMMY_SERVICE,
        )
        self.assertEqual(response.status_code, 403)

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

    def test_manager_can_add_to_any_structure_inside_its_department(self):
        self.client.force_authenticate(user=self.manager)
        slug = make_structure(department="31").slug
        Structure.objects.get(slug=slug)
        DUMMY_SERVICE["structure"] = slug
        response = self.client.post(
            "/services/",
            DUMMY_SERVICE,
        )
        self.assertEqual(response.status_code, 201)
        slug = response.data["slug"]
        Service.objects.get(slug=slug)

    def test_manager_cant_add_to_any_structure_outside_its_department(self):
        self.client.force_authenticate(user=self.manager)
        slug = make_structure(department="44").slug
        Structure.objects.get(slug=slug)
        DUMMY_SERVICE["structure"] = slug
        response = self.client.post(
            "/services/",
            DUMMY_SERVICE,
        )
        self.assertEqual(response.status_code, 403)

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

    def test_manager_see_all_choices_inside_its_department(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.get(
            "/services-options/",
        )
        conds = [d["value"] for d in response.data["access_conditions"]]

        self.assertIn(self.global_condition1.id, conds)
        self.assertIn(self.global_condition2.id, conds)
        self.assertIn(self.struct_31_condition1.id, conds)
        self.assertIn(self.struct_31_condition2.id, conds)

    def test_manager_cant_see_choices_outside_its_department(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.get(
            "/services-options/",
        )
        conds = [d["value"] for d in response.data["access_conditions"]]

        self.assertNotIn(self.struct_condition1.id, conds)
        self.assertNotIn(self.struct_condition2.id, conds)
        self.assertNotIn(self.other_struct_condition1.id, conds)
        self.assertNotIn(self.other_struct_condition2.id, conds)

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

    def test_manager_can_add_struct_choice_inside_its_department(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(
            f"/services/{self.service_31.slug}/",
            {"access_conditions": [self.struct_31_condition1.id]},
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/services/{self.service_31.slug}/")
        self.assertEqual(
            response.data["access_conditions"], [self.struct_31_condition1.id]
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
        self.assertEqual(hitem.fields, ["address1", "name"])

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

    def test_members_dont_see_archived_services_count(self):
        user = baker.make("users.User", is_valid=True)
        structure = make_structure(user)
        service = make_service(status=ServiceStatus.PUBLISHED, structure=structure)
        make_service(status=ServiceStatus.PUBLISHED, structure=structure)
        make_service(status=ServiceStatus.ARCHIVED, structure=structure)
        self.client.force_authenticate(user=user)
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["structure_info"]["num_services"], 2)

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

    def test_su_dont_see_archived_services_count(self):
        user = baker.make("users.User", is_valid=True)
        structure = make_structure(user)
        service = make_service(status=ServiceStatus.PUBLISHED, structure=structure)
        make_service(status=ServiceStatus.PUBLISHED, structure=structure)
        make_service(status=ServiceStatus.ARCHIVED, structure=structure)
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["structure_info"]["num_services"], 2)

    def test_manager_see_all_services_count_inside_its_department(self):
        user = baker.make("users.User", is_valid=True)
        structure = make_structure(user, department="31")
        service = make_service(status=ServiceStatus.PUBLISHED, structure=structure)
        make_service(status=ServiceStatus.PUBLISHED, structure=structure)
        make_service(status=ServiceStatus.DRAFT, structure=structure)
        self.client.force_authenticate(user=self.manager)
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["structure_info"]["num_services"], 3)

    def test_manager_see_public_services_count_outside_its_department(self):
        user = baker.make("users.User", is_valid=True)
        structure = make_structure(user, department="44")
        service = make_service(status=ServiceStatus.PUBLISHED, structure=structure)
        make_service(status=ServiceStatus.PUBLISHED, structure=structure)
        make_service(status=ServiceStatus.DRAFT, structure=structure)
        self.client.force_authenticate(user=self.manager)
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["structure_info"]["num_services"], 2)

    def test_manager_dont_see_archived_services_count_inside_its_department(self):
        user = baker.make("users.User", is_valid=True)
        structure = make_structure(user, department="31")
        service = make_service(status=ServiceStatus.PUBLISHED, structure=structure)
        make_service(status=ServiceStatus.PUBLISHED, structure=structure)
        make_service(status=ServiceStatus.ARCHIVED, structure=structure)
        self.client.force_authenticate(user=self.manager)
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["structure_info"]["num_services"], 2)

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


class DataInclusionSearchTestCase(APITestCase):
    def setUp(self):
        self.region = baker.make("Region", code="99")
        self.dept = baker.make("Department", region=self.region.code, code="77")
        self.epci11 = baker.make("EPCI", code="11111")
        self.epci12 = baker.make("EPCI", code="22222")
        self.city1 = baker.make(
            "City",
            name="Sainte Jacquelineboeuf",
            code="12345",
            epcis=[self.epci11.code, self.epci12.code],
            department=self.dept.code,
            region=self.region.code,
        )
        self.city2 = baker.make("City")

        self.di_client = FakeDataInclusionClient()
        self.factory = APIRequestFactory()
        self.search = lambda request: search(request, di_client=self.di_client)

    def make_di_service(self, **kwargs) -> dict:
        service_data = make_di_service_data(**kwargs)
        self.di_client.services.append(service_data)
        return service_data

    @staticmethod
    def get_di_id(service_data: dict) -> str:
        return service_data["source"] + "--" + service_data["id"]

    def test_find_services_in_city(self):
        service_data = self.make_di_service(
            zone_diffusion_type="commune",
            zone_diffusion_code=self.city1.code,
        )
        request = self.factory.get("/search/", {"city": self.city1.code})
        response = self.search(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], service_data["id"])

    def test_dont_find_services_in_other_city(self):
        self.make_di_service(
            zone_diffusion_type="commune",
            zone_diffusion_code=self.city1.code,
        )
        request = self.factory.get("/search/", {"city": self.city2.code})
        response = self.search(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_filter_by_fee(self):
        service_data = self.make_di_service(
            zone_diffusion_type="pays", frais=["gratuit"]
        )
        self.make_di_service(zone_diffusion_type="pays", frais=["payant"])
        request = self.factory.get(
            "/search/",
            {
                "di": True,
                "city": self.city2.code,
                "fees": ServiceFee.objects.filter(value="gratuit").first().value,
            },
        )
        response = self.search(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], service_data["id"])

    def test_filter_by_kind(self):
        service_data = self.make_di_service(
            zone_diffusion_type="pays", types=["atelier", "accompagnement"]
        )
        self.make_di_service(zone_diffusion_type="pays", types=["formation"])
        request = self.factory.get(
            "/search/",
            {
                "di": True,
                "city": self.city2.code,
                "kinds": ServiceKind.objects.filter(value=service_data["types"][0])
                .first()
                .value,
            },
        )
        response = self.search(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], service_data["id"])

    def test_filter_by_cat(self):
        service_data_1 = self.make_di_service(
            zone_diffusion_type="pays",
            thematiques=["famille", "sante"],
        )
        service_data_2 = self.make_di_service(
            zone_diffusion_type="pays",
            thematiques=["famille--garde-denfants"],
        )
        self.make_di_service(zone_diffusion_type="pays", thematiques=["numerique"])
        request = self.factory.get(
            "/search/",
            {
                "di": True,
                "city": self.city2.code,
                "cats": "famille",
            },
        )
        response = self.search(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["id"], service_data_1["id"])
        self.assertEqual(response.data[1]["id"], service_data_2["id"])

    def test_simple_search_with_data_inclusion(self):
        service_data = self.make_di_service(code_insee=self.city1.code)
        request = self.factory.get("/search/", {"city": self.city1.code})
        response = self.search(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["distance"], 0)
        self.assertEqual(response.data[0]["id"], service_data["id"])

    def test_simple_search_with_data_inclusion_and_dora(self):
        service_dora = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.CITY,
            diffusion_zone_details=self.city1.code,
        )
        service_data = self.make_di_service(code_insee=self.city1.code)
        request = self.factory.get("/search/", {"city": self.city1.code})
        response = self.search(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["slug"], service_dora.slug)
        self.assertEqual(response.data[1]["id"], service_data["id"])

    def test_data_inclusion_connection_error(self):
        service_dora = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.CITY,
            diffusion_zone_details=self.city1.code,
        )

        class FaultyDataInclusionClient:
            def search_services(self, **kwargs):
                raise requests.ConnectionError()

        di_client = FaultyDataInclusionClient()
        request = self.factory.get("/search/", {"city": self.city1.code})
        response = search(request, di_client=di_client)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service_dora.slug)

    def test_on_site_first(self):
        self.make_di_service(
            zone_diffusion_type="pays", modes_accueil=["en-presentiel"]
        )
        service_data_2 = self.make_di_service(
            zone_diffusion_type="pays", modes_accueil=["a-distance"]
        )
        self.make_di_service(
            zone_diffusion_type="pays", modes_accueil=["en-presentiel"]
        )
        request = self.factory.get("/search/", {"city": "12345"})
        response = self.search(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[2]["id"], service_data_2["id"])

    def test_dora_first(self):
        toulouse_center = Point(1.4436700, 43.6042600, srid=4326)
        # Points à moins de 100km de Toulouse
        point_in_toulouse = Point(1.4187594455116272, 43.601528176416416, srid=4326)

        region = baker.make("Region", code="76")
        dept = baker.make("Department", region=region.code, code="31")
        toulouse = baker.make(
            "City",
            code="31555",
            department=dept.code,
            region=region.code,
            # la valeur du buffer est complètement approximative
            # elle permet juste de valider les assertions suivantes
            geom=MultiPolygon(toulouse_center.buffer(0.05)),
        )

        service_instance_1 = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
        )
        service_instance_1.location_kinds.set(
            [LocationKind.objects.get(value="a-distance")]
        )
        service_instance_2 = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            geom=point_in_toulouse,
        )
        service_instance_2.location_kinds.set(
            [LocationKind.objects.get(value="en-presentiel")]
        )
        service_data_3 = self.make_di_service(
            zone_diffusion_type="pays", modes_accueil=["a-distance"]
        )
        service_data_4 = self.make_di_service(
            zone_diffusion_type="pays", modes_accueil=["en-presentiel"]
        )
        request = self.factory.get("/search/", {"city": toulouse.code})
        response = self.search(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)
        self.assertEqual(response.data[0]["slug"], service_instance_2.slug)
        self.assertEqual(response.data[1]["id"], service_data_4["id"])
        self.assertEqual(response.data[2]["slug"], service_instance_1.slug)
        self.assertEqual(response.data[3]["id"], service_data_3["id"])

    @override_settings(DATA_INCLUSION_STREAM_SOURCES=["foo"])
    def test_search_target_sources(self):
        service_data = self.make_di_service(source="foo", zone_diffusion_type="pays")
        self.make_di_service(source="bar", zone_diffusion_type="pays")
        request = self.factory.get("/search/", {"city": self.city1.code})
        response = self.search(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], service_data["id"])

    def test_service_di_contains_service_fields(self):
        service_data = self.make_di_service()
        di_id = self.get_di_id(service_data)
        request = self.factory.get(f"/service-di/{di_id}/")
        response = service_di(request, di_id=di_id, di_client=self.di_client)

        for field in set(ServiceSerializer.Meta.fields) - set(
            ["category", "category_display"]
        ):
            with self.subTest(field=field):
                self.assertIn(field, response.data)

    def test_service_di_address(self):
        service_data = self.make_di_service(
            adresse="chemin de Ferreira",
            complement_adresse="2ème étage",
            code_insee="59999",
            code_postal="59998",
            commune="Sainte Jacquelineboeuf",
            longitude=-61.64115,
            latitude=9.8741475,
        )
        di_id = self.get_di_id(service_data)
        request = self.factory.get(f"/service-di/{di_id}/")
        response = service_di(request, di_id=di_id, di_client=self.di_client)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["address1"], service_data["adresse"])
        self.assertEqual(response.data["address2"], service_data["complement_adresse"])
        self.assertEqual(response.data["city_code"], service_data["code_insee"])
        self.assertEqual(response.data["postal_code"], service_data["code_postal"])
        self.assertEqual(response.data["city"], service_data["commune"])
        self.assertEqual(response.data["geom"], None)
        self.assertEqual(response.data["department"], "59")

    def test_service_di_categories(self):
        cases = [
            (None, None, None, None, None),
            ([], [], [], [], []),
            (
                ["mobilite", "famille--garde-denfants"],
                ["mobilite"],
                ["Mobilité"],
                ["famille--garde-denfants"],
                ["Garde d'enfants"],
            ),
        ]
        for (
            thematiques,
            categories,
            categories_display,
            subcategories,
            subcategories_display,
        ) in cases:
            with self.subTest(thematiques=thematiques):
                service_data = self.make_di_service(thematiques=thematiques)
                di_id = self.get_di_id(service_data)
                request = self.factory.get(f"/service-di/{di_id}/")
                response = service_di(request, di_id=di_id, di_client=self.di_client)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["categories"], categories)
                self.assertEqual(
                    response.data["categories_display"], categories_display
                )
                self.assertEqual(response.data["subcategories"], subcategories)
                self.assertEqual(
                    response.data["subcategories_display"], subcategories_display
                )

    def test_service_di_beneficiaries_access_modes(self):
        courriel_mode_instance = BeneficiaryAccessMode.objects.get(
            value="envoyer-courriel"
        )

        cases = [
            (None, None, None),
            ([], [], []),
            (
                ["envoyer-un-mail"],
                [courriel_mode_instance.value],
                [courriel_mode_instance.label],
            ),
        ]
        for (
            modes_orientation_beneficiaire,
            beneficiaries_access_modes,
            beneficiaries_access_modes_display,
        ) in cases:
            with self.subTest(
                modes_orientation_beneficiaire=modes_orientation_beneficiaire
            ):
                service_data = self.make_di_service(
                    modes_orientation_beneficiaire=modes_orientation_beneficiaire
                )
                di_id = self.get_di_id(service_data)
                request = self.factory.get(f"/service-di/{di_id}/")
                response = service_di(request, di_id=di_id, di_client=self.di_client)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.data["beneficiaries_access_modes"],
                    beneficiaries_access_modes,
                )
                self.assertEqual(
                    response.data["beneficiaries_access_modes_display"],
                    beneficiaries_access_modes_display,
                )

    def test_service_di_beneficiaries_access_modes_other(self):
        service_data = self.make_di_service(
            modes_orientation_beneficiaire_autres="Nous consulter"
        )
        di_id = self.get_di_id(service_data)
        request = self.factory.get(f"/service-di/{di_id}/")
        response = service_di(request, di_id=di_id, di_client=self.di_client)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["beneficiaries_access_modes_other"], "Nous consulter"
        )

    def test_service_di_coach_orientation_modes(self):
        courriel_mode_instance = CoachOrientationMode.objects.get(
            value="envoyer-courriel"
        )

        cases = [
            (None, None, None),
            ([], [], []),
            (
                ["envoyer-un-mail"],
                [courriel_mode_instance.value],
                [courriel_mode_instance.label],
            ),
        ]
        for (
            modes_orientation_accompagnateur,
            coach_orientation_modes,
            coach_orientation_modes_display,
        ) in cases:
            with self.subTest(
                modes_orientation_accompagnateur=modes_orientation_accompagnateur
            ):
                service_data = self.make_di_service(
                    modes_orientation_accompagnateur=modes_orientation_accompagnateur
                )
                di_id = self.get_di_id(service_data)
                request = self.factory.get(f"/service-di/{di_id}/")
                response = service_di(request, di_id=di_id, di_client=self.di_client)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.data["coach_orientation_modes"], coach_orientation_modes
                )
                self.assertEqual(
                    response.data["coach_orientation_modes_display"],
                    coach_orientation_modes_display,
                )

    def test_service_di_coach_orientation_modes_other(self):
        service_data = self.make_di_service(
            modes_orientation_accompagnateur_autres="Nous consulter"
        )
        di_id = self.get_di_id(service_data)
        request = self.factory.get(f"/service-di/{di_id}/")
        response = service_di(request, di_id=di_id, di_client=self.di_client)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["coach_orientation_modes_other"], "Nous consulter"
        )

    def test_service_di_concerned_public(self):
        cases = [
            (None, None, None),
            ([], [], []),
            (["valeur-inconnue"], [], []),
            (["jeunes-16-26"], ["jeunes-16-26"], ["Jeunes (16-26 ans)"]),
        ]
        for profils, concerned_public, concerned_public_display in cases:
            with self.subTest(profils=profils):
                service_data = self.make_di_service(profils=profils)
                di_id = self.get_di_id(service_data)
                request = self.factory.get(f"/service-di/{di_id}/")
                response = service_di(request, di_id=di_id, di_client=self.di_client)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["concerned_public"], concerned_public)
                self.assertEqual(
                    response.data["concerned_public_display"], concerned_public_display
                )

    def test_service_di_contact(self):
        cases = [
            (None, None, None, None),
            ("foo@bar.baz", "David Rocher", "0102030405", True),
        ]
        for courriel, contact_nom_prenom, telephone, contact_public in cases:
            with self.subTest(
                courriel=courriel,
                contact_nom_prenom=contact_nom_prenom,
                telephone=telephone,
                contact_public=contact_public,
            ):
                service_data = self.make_di_service(
                    courriel=courriel,
                    contact_nom_prenom=contact_nom_prenom,
                    telephone=telephone,
                    contact_public=contact_public,
                )
                di_id = self.get_di_id(service_data)
                request = self.factory.get(f"/service-di/{di_id}/")
                response = service_di(request, di_id=di_id, di_client=self.di_client)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["contact_email"], courriel)
                self.assertEqual(response.data["contact_name"], contact_nom_prenom)
                self.assertEqual(response.data["contact_phone"], telephone)
                self.assertEqual(
                    response.data["is_contact_info_public"], contact_public
                )

    def test_service_di_credentials(self):
        cases = [
            (None, None, None),
            ([], [], []),
            (["lorem", "ipsum"], ["lorem", "ipsum"], ["lorem", "ipsum"]),
        ]
        for justificatifs, credentials, credentials_display in cases:
            with self.subTest(justificatifs=justificatifs):
                service_data = self.make_di_service(justificatifs=justificatifs)
                di_id = self.get_di_id(service_data)
                request = self.factory.get(f"/service-di/{di_id}/")
                response = service_di(request, di_id=di_id, di_client=self.di_client)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["credentials"], credentials)
                self.assertEqual(
                    response.data["credentials_display"], credentials_display
                )

    def test_service_di_diffusion_zone(self):
        cases = [
            (
                None,
                None,
                None,
                "",
                None,
                "",
            ),
            (
                "commune",
                self.city1.code,
                self.city1.code,
                f"{self.city1.name} ({self.dept.code})",
                AdminDivisionType.CITY.value,
                AdminDivisionType.CITY.label,
            ),
            (
                "pays",
                None,
                None,
                "France entière",
                AdminDivisionType.COUNTRY.value,
                AdminDivisionType.COUNTRY.label,
            ),
        ]

        for (
            zone_diffusion_type,
            zone_diffusion_code,
            diffusion_zone_details,
            diffusion_zone_details_display,
            diffusion_zone_type,
            diffusion_zone_type_display,
        ) in cases:
            with self.subTest(
                zone_diffusion_type=zone_diffusion_type,
                zone_diffusion_code=zone_diffusion_code,
            ):
                service_data = self.make_di_service(
                    zone_diffusion_type=zone_diffusion_type,
                    zone_diffusion_code=zone_diffusion_code,
                )
                di_id = self.get_di_id(service_data)
                request = self.factory.get(f"/service-di/{di_id}/")
                response = service_di(request, di_id=di_id, di_client=self.di_client)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.data["diffusion_zone_details"], diffusion_zone_details
                )
                self.assertEqual(
                    response.data["diffusion_zone_details_display"],
                    diffusion_zone_details_display,
                )
                self.assertEqual(
                    response.data["diffusion_zone_type"], diffusion_zone_type
                )
                self.assertEqual(
                    response.data["diffusion_zone_type_display"],
                    diffusion_zone_type_display,
                )
                self.assertEqual(response.data["qpv_or_zrr"], None)

    def test_service_di_fee(self):
        cases = [
            (None, None),
            ([], ""),
            (["gratuit", "adhesion"], "gratuit, adhesion"),
        ]
        for frais, fee_condition in cases:
            with self.subTest(frais=frais):
                service_data = self.make_di_service(frais=frais)
                di_id = self.get_di_id(service_data)
                request = self.factory.get(f"/service-di/{di_id}/")
                response = service_di(request, di_id=di_id, di_client=self.di_client)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["fee_condition"], fee_condition)

        cases = [
            (None, None),
            ("", ""),
            ("Gratuit pour tous", "Gratuit pour tous"),
        ]
        for frais_autres, fee_details in cases:
            with self.subTest(frais_autres=frais_autres):
                service_data = self.make_di_service(frais_autres=frais_autres)
                di_id = self.get_di_id(service_data)
                request = self.factory.get(f"/service-di/{di_id}/")
                response = service_di(request, di_id=di_id, di_client=self.di_client)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["fee_details"], fee_details)

    def test_service_di_location_kinds(self):
        cases = [
            (None, None, None),
            ([], [], []),
            (["en-presentiel"], ["en-presentiel"], ["En présentiel"]),
        ]
        for modes_accueil, location_kinds, location_kinds_display in cases:
            with self.subTest(modes_accueil=modes_accueil):
                service_data = self.make_di_service(modes_accueil=modes_accueil)
                di_id = self.get_di_id(service_data)
                request = self.factory.get(f"/service-di/{di_id}/")
                response = service_di(request, di_id=di_id, di_client=self.di_client)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["location_kinds"], location_kinds)
                self.assertEqual(
                    response.data["location_kinds_display"], location_kinds_display
                )

    def test_service_di_requirements(self):
        cases = [
            (None, None, None),
            ([], [], []),
            (["lorem", "ipsum"], ["lorem", "ipsum"], ["lorem", "ipsum"]),
        ]
        for pre_requis, requirements, requirements_display in cases:
            with self.subTest(pre_requis=pre_requis):
                service_data = self.make_di_service(pre_requis=pre_requis)
                di_id = self.get_di_id(service_data)
                request = self.factory.get(f"/service-di/{di_id}/")
                response = service_di(request, di_id=di_id, di_client=self.di_client)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["requirements"], requirements)
                self.assertEqual(
                    response.data["requirements_display"], requirements_display
                )

    def test_service_di_kinds(self):
        cases = [
            (None, None, None),
            ([], [], []),
            (["accompagnement"], ["accompagnement"], ["Accompagnement"]),
        ]
        for types, kinds, kinds_display in cases:
            with self.subTest(types=types):
                service_data = self.make_di_service(types=types)
                di_id = self.get_di_id(service_data)
                request = self.factory.get(f"/service-di/{di_id}/")
                response = service_di(request, di_id=di_id, di_client=self.di_client)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["kinds"], kinds)
                self.assertEqual(response.data["kinds_display"], kinds_display)

    def test_service_di_desc(self):
        cases = [
            (None, ""),
            ("", ""),
            ("Lorem ipsum", "Lorem ipsum"),
        ]

        for presentation, desc in cases:
            with self.subTest(presentation=presentation):
                service_data = self.make_di_service(
                    nom="L.I.",
                    presentation_resume=presentation,
                    presentation_detail=presentation,
                )
                di_id = self.get_di_id(service_data)
                request = self.factory.get(f"/service-di/{di_id}/")
                response = service_di(request, di_id=di_id, di_client=self.di_client)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["name"], service_data["nom"])
                self.assertEqual(response.data["full_desc"], desc)
                self.assertEqual(response.data["short_desc"], desc)

    def test_service_di_date(self):
        service_data = self.make_di_service(
            date_creation="2022-01-01",
            date_maj="2023-01-01",
            recurrence="Tous les jours",
            date_suspension="2030-01-01",
            structure={"nom": "Rouge Empire"},
        )
        di_id = self.get_di_id(service_data)
        request = self.factory.get(f"/service-di/{di_id}/")
        response = service_di(request, di_id=di_id, di_client=self.di_client)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["creation_date"], service_data["date_creation"])
        self.assertEqual(response.data["modification_date"], service_data["date_maj"])
        self.assertEqual(response.data["publication_date"], None)
        self.assertEqual(response.data["recurrence"], service_data["recurrence"])
        self.assertEqual(
            response.data["suspension_date"], service_data["date_suspension"]
        )
        self.assertEqual(response.data["publication_date"], None)

    def test_service_di_structure(self):
        service_data = self.make_di_service(
            structure_id="rouge-empire",
            structure={"nom": "Rouge Empire"},
        )
        di_id = self.get_di_id(service_data)
        request = self.factory.get(f"/service-di/{di_id}/")
        response = service_di(request, di_id=di_id, di_client=self.di_client)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["structure"], service_data["structure_id"])
        self.assertEqual(
            response.data["structure_info"]["name"], service_data["structure"]["nom"]
        )

    def test_service_di_is_cumulative(self):
        for cumulable in [True, False, None]:
            with self.subTest(cumulable=cumulable):
                service_data = self.make_di_service(cumulable=cumulable)
                di_id = self.get_di_id(service_data)
                request = self.factory.get(f"/service-di/{di_id}/")
                response = service_di(request, di_id=di_id, di_client=self.di_client)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["is_cumulative"], cumulable)

    def test_service_di_update_status(self):
        cases = [
            (str(timezone.now().date() - timedelta(days=365)), "REQUIRED"),
            (str(timezone.now().date()), "NOT_NEEDED"),
        ]
        for date_maj, update_status in cases:
            with self.subTest(update_status=update_status):
                service_data = self.make_di_service(date_maj=date_maj)
                di_id = self.get_di_id(service_data)
                request = self.factory.get(f"/service-di/{di_id}/")
                response = service_di(request, di_id=di_id, di_client=self.di_client)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["update_status"], update_status)

    def test_service_di_misc(self):
        service_data = self.make_di_service()
        di_id = self.get_di_id(service_data)
        request = self.factory.get(f"/service-di/{di_id}/")
        response = service_di(request, di_id=di_id, di_client=self.di_client)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["can_write"], False)
        self.assertEqual(response.data["has_already_been_unpublished"], None)
        self.assertEqual(response.data["is_available"], True)
        self.assertEqual(response.data["model"], None)
        self.assertEqual(response.data["model_changed"], None)
        self.assertEqual(response.data["model_name"], None)
        self.assertEqual(response.data["online_form"], None)
        self.assertEqual(response.data["remote_url"], None)
        self.assertEqual(response.data["status"], "PUBLISHED")
        self.assertEqual(response.data["use_inclusion_numerique_scheme"], False)


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

        baker.make("ServiceCategory", value="cat1", label="cat1")
        baker.make("ServiceSubCategory", value="cat1--sub1", label="cat1--sub1")
        baker.make("ServiceSubCategory", value="cat1--sub2", label="cat1--sub2")
        baker.make("ServiceSubCategory", value="cat1--sub3", label="cat1--sub3")
        baker.make("ServiceSubCategory", value="cat1--autre", label="cat1--autre")
        baker.make("ServiceCategory", value="cat2", label="cat2")
        baker.make("ServiceSubCategory", value="cat2--sub1", label="cat2--sub1")
        baker.make("ServiceSubCategory", value="cat2--sub2", label="cat2--sub2")
        baker.make("ServiceSubCategory", value="cat2--autre", label="cat2--autre")
        baker.make("ServiceCategory", value="cat3", label="cat3")

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

    def test_filter_by_fee_free(self):
        service1 = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            fee_condition=ServiceFee.objects.filter(value="gratuit").first(),
        )
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            fee_condition=ServiceFee.objects.filter(value="payant").first(),
        )
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            fee_condition=ServiceFee.objects.filter(
                value="gratuit-sous-conditions"
            ).first(),
        )
        response = self.client.get(f"/search/?city={self.city1.code}&fees=gratuit")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service1.slug)

    def test_filter_by_fee_payant(self):
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            fee_condition=ServiceFee.objects.filter(value="gratuit").first(),
        )
        service2 = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            fee_condition=ServiceFee.objects.filter(value="payant").first(),
        )
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            fee_condition=ServiceFee.objects.filter(
                value="gratuit-sous-conditions"
            ).first(),
        )
        response = self.client.get(f"/search/?city={self.city1.code}&fees=payant")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service2.slug)

    def test_filter_by_fee_gratuit_sous_condition(self):
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            fee_condition=ServiceFee.objects.filter(value="gratuit").first(),
        )
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            fee_condition=ServiceFee.objects.filter(value="payant").first(),
        )
        service3 = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            fee_condition=ServiceFee.objects.filter(
                value="gratuit-sous-conditions"
            ).first(),
        )
        response = self.client.get(
            f"/search/?city={self.city1.code}&fees=gratuit-sous-conditions"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service3.slug)

    def test_filter_without_fee(self):
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            fee_condition=ServiceFee.objects.filter(value="gratuit").first(),
        )
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            fee_condition=ServiceFee.objects.filter(value="payant").first(),
        )
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            fee_condition=ServiceFee.objects.filter(
                value="gratuit-sous-conditions"
            ).first(),
        )
        response = self.client.get(f"/search/?city={self.city1.code}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)

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

    def test_find_service_with_requested_cat(self):
        service = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            categories="cat1",
        )
        response = self.client.get(f"/search/?city={self.city1.code}&cats=cat1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service.slug)

    def test_find_service_with_requested_cats(self):
        service_1 = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            categories="cat1",
        )
        service_2 = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            categories="cat2",
        )
        response = self.client.get(f"/search/?city={self.city1.code}&cats=cat1,cat2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        response_slugs = sorted([s["slug"] for s in response.data])
        self.assertEqual(response_slugs, sorted([service_1.slug, service_2.slug]))

    def test_find_service_with_requested_cats_exclude_one(self):
        service_1 = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            categories="cat1",
        )
        service_2 = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            categories="cat2",
        )
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            categories="cat3",
        )
        response = self.client.get(f"/search/?city={self.city1.code}&cats=cat1,cat2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        response_slugs = sorted([s["slug"] for s in response.data])
        self.assertEqual(response_slugs, sorted([service_1.slug, service_2.slug]))

    def test_dont_find_service_without_requested_cat(self):
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            categories="cat1",
        )

        response = self.client.get(f"/search/?city={self.city1.code}&cats=cat2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_find_service_with_requested_subcat(self):
        service = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            subcategories="cat1--sub1",
        )
        response = self.client.get(f"/search/?city={self.city1.code}&subs=cat1--sub1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service.slug)

    def test_find_service_with_requested_subcats(self):
        service_1 = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            subcategories="cat1--sub1",
        )
        service_2 = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            subcategories="cat1--sub2",
        )
        response = self.client.get(
            f"/search/?city={self.city1.code}&subs=cat1--sub1,cat1--sub2"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        response_slugs = sorted([s["slug"] for s in response.data])
        self.assertEqual(response_slugs, sorted([service_1.slug, service_2.slug]))

    def test_find_service_with_requested_subcats_different_cats(self):
        service_1 = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            subcategories="cat1--sub1",
        )
        service_2 = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            subcategories="cat1--sub2",
        )
        service_3 = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            subcategories="cat2--sub1",
        )
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            subcategories="cat2--sub2",
        )
        response = self.client.get(
            f"/search/?city={self.city1.code}&subs=cat1--sub1,cat1--sub2,cat2--sub1"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)
        response_slugs = sorted([s["slug"] for s in response.data])
        self.assertEqual(
            response_slugs, sorted([service_1.slug, service_2.slug, service_3.slug])
        )

    def test_find_service_with_requested_subcats_exclude_one(self):
        service_1 = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            subcategories="cat1--sub1",
        )
        service_2 = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            subcategories="cat1--sub2",
        )
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            subcategories="cat1--sub3",
        )
        response = self.client.get(
            f"/search/?city={self.city1.code}&subs=cat1--sub1,cat1--sub2"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        response_slugs = sorted([s["slug"] for s in response.data])
        self.assertEqual(response_slugs, sorted([service_1.slug, service_2.slug]))

    def test_dont_find_service_without_requested_subcat(self):
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            subcategories="cat1--sub1",
        )

        response = self.client.get(f"/search/?city={self.city1.code}&subs=cat1--sub2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_find_service_with_no_subcat_when_looking_for_the__other__subcat(self):
        # On veut remonter les services sans sous-catégorie quand on interroge la
        # sous-catégorie 'autres'
        service = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            categories="cat1",
        )
        response = self.client.get(f"/search/?city={self.city1.code}&subs=cat1--autre")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service.slug)

    def test_find_service_with_no_subcat_when_looking_for_the__other__subcat_2(
        self,
    ):
        # On veut remonter les services sans sous-catégorie **de la même catégorie**
        # quand on interroge la sous-catégorie 'autres'
        service = make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            categories="cat1,cat2",
            subcategories="cat2--sub1",
        )
        response = self.client.get(f"/search/?city={self.city1.code}&subs=cat1--autre")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], service.slug)

    def test_dont_find_service_with_no_subcat_when_looking_for_any_subcat(self):
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            categories="cat1",
        )
        response = self.client.get(f"/search/?city={self.city1.code}&subs=cat1--sub1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_find_cats_and_subcats_are_independant(self):
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            categories="cat1",
            subcategories="cat1--sub1",
        )
        make_service(
            status=ServiceStatus.PUBLISHED,
            diffusion_zone_type=AdminDivisionType.COUNTRY,
            categories="cat2",
            subcategories="cat2--sub1",
        )
        response = self.client.get(
            f"/search/?city={self.city1.code}&cats=cat1&subs=cat2--sub1"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)


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
            elif field == "fee_condition":
                new_val = "payant"
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


class ServiceUpdateStatusTestCase(APITestCase):
    def test_draft_service_update_status_as_not_needed(self):
        # ÉTANT DONNÉ un service en brouillon, modifié il y a un an
        user = baker.make("users.User", is_valid=True)
        structure = make_structure(user)
        service = make_service(
            status=ServiceStatus.DRAFT,
            modification_date=timezone.now() - timedelta(days=12 * 30),
            structure=structure,
        )
        self.client.force_authenticate(user=user)

        # QUAND je récupère ce service
        response = self.client.get(f"/services/{service.slug}/")

        # ALORS son statut d'actualisation est "NOT_NEEDED"
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["update_status"], "NOT_NEEDED")

    def test_archived_service_update_status(self):
        # ÉTANT DONNÉ un service en archivé, modifié il y a un an
        user = baker.make("users.User", is_valid=True)
        structure = make_structure(user)
        service = make_service(
            status=ServiceStatus.ARCHIVED,
            modification_date=timezone.now() - timedelta(days=12 * 30),
            structure=structure,
        )
        self.client.force_authenticate(user=user)

        # QUAND je récupère ce service
        response = self.client.get(f"/services/{service.slug}/")

        # ALORS son statut d'actualisation est "NOT_NEEDED"
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["update_status"], "NOT_NEEDED")

    def test_suggestion_service_update_status(self):
        # ÉTANT DONNÉ un service suggéré, modifié il y a un an
        user = baker.make("users.User", is_valid=True)
        structure = make_structure(user)
        service = make_service(
            status=ServiceStatus.SUGGESTION,
            modification_date=timezone.now() - timedelta(days=12 * 30),
            structure=structure,
        )
        self.client.force_authenticate(user=user)

        # QUAND je récupère ce service
        response = self.client.get(f"/services/{service.slug}/")

        # ALORS son statut d'actualisation est "NOT_NEEDED"
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["update_status"], "NOT_NEEDED")

    def test_published_service_update_status_required(self):
        # ÉTANT DONNÉ un service suggéré, modifié il y a 9 mois
        service = make_service(
            status=ServiceStatus.PUBLISHED,
            modification_date=timezone.now() - timedelta(days=9 * 30),
        )

        # QUAND je récupère ce service
        response = self.client.get(f"/services/{service.slug}/")

        # ALORS son statut d'actualisation est "REQUIRED"
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["update_status"], "REQUIRED")

    def test_published_service_update_status_needed(self):
        # ÉTANT DONNÉ un service suggéré, modifié il y a 7 mois
        service = make_service(
            status=ServiceStatus.PUBLISHED,
            modification_date=timezone.now() - timedelta(days=7 * 30),
        )

        # QUAND je récupère ce service
        response = self.client.get(f"/services/{service.slug}/")

        # ALORS son statut d'actualisation est "NEEDED"
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["update_status"], "NEEDED")

    def test_published_service_update_status_not_needed(self):
        # ÉTANT DONNÉ un service suggéré, modifié il y a 9 mois
        service = make_service(
            status=ServiceStatus.PUBLISHED,
            modification_date=timezone.now() - timedelta(days=1 * 30),
        )

        # QUAND je récupère ce service
        response = self.client.get(f"/services/{service.slug}/")

        # ALORS son statut d'actualisation est "NOT_NEEDED"
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["update_status"], "NOT_NEEDED")


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

    def test_create_service_kind(self):
        # ÉTANT DONNÉ un type de service non existant
        value = "new-value"
        label = "Nouvelle valeur"
        self.assertEqual(ServiceKind.objects.filter(value=value).count(), 0)

        # QUAND je créé ce type de service
        create_service_kind(ServiceKind, value, label)

        # ALORS il existe
        subcategory = ServiceKind.objects.filter(value=value)
        self.assertEqual(subcategory.count(), 1)
        self.assertEqual(subcategory.first().value, value)
        self.assertEqual(subcategory.first().label, label)

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

    def test_rename_subcategory(self):
        value = "value"
        new_label = "new_label"

        # ÉTANT DONNÉ un besoin existant
        baker.make("ServiceSubCategory", value=value, label="Label_1")

        # QUAND je modifie son nom
        rename_subcategory(
            ServiceSubCategory,
            value=value,
            new_label=new_label,
        )

        # ALORS le besoin est correctement renommé
        subcategory = ServiceSubCategory.objects.filter(value=value)
        self.assertEqual(subcategory.count(), 1)
        self.assertEqual(subcategory.first().value, value)
        self.assertEqual(subcategory.first().label, new_label)

    def test_update_category_value_and_label_value(self):
        old_value = "old_value"
        new_value = "new_value"
        new_label = "new_label"

        # ÉTANT DONNÉ une thématique existante
        baker.make("ServiceCategory", value=old_value, label="Label_1")
        self.assertEqual(ServiceCategory.objects.filter(value=old_value).count(), 1)

        # QUAND je la modifie
        update_category_value_and_label(
            ServiceCategory,
            ServiceSubCategory,
            old_value=old_value,
            new_value=new_value,
            new_label=new_label,
            migrate_subcategories=False,
        )

        # ALORS la thématique est correctement modifiée
        self.assertEqual(ServiceCategory.objects.filter(value=old_value).count(), 0)

        category = ServiceCategory.objects.filter(value=new_value)
        self.assertEqual(category.count(), 1)
        self.assertEqual(category.first().value, new_value)
        self.assertEqual(category.first().label, new_label)

    def test_update_category_value_and_label_value_with_subcategories(self):
        old_value = "old_value"
        new_value = "new_value"
        new_label = "new_label"

        # ÉTANT DONNÉ une thématique existante
        baker.make("ServiceCategory", value=old_value, label="Label_1")
        self.assertEqual(ServiceCategory.objects.filter(value=old_value).count(), 1)

        # ET deux besoins associés
        old_subcategory_value_1 = f"{old_value}--subcategory_1"
        old_subcategory_value_2 = f"{old_value}--subcategory_2"
        new_subcategory_value_1 = f"{new_value}--subcategory_1"
        new_subcategory_value_2 = f"{new_value}--subcategory_2"
        baker.make("ServiceSubCategory", value=old_subcategory_value_1)
        baker.make("ServiceSubCategory", value=old_subcategory_value_2)

        # QUAND je la modifie
        update_category_value_and_label(
            ServiceCategory,
            ServiceSubCategory,
            old_value=old_value,
            new_value=new_value,
            new_label=new_label,
        )

        # ALORS la thématique est correctement modifiée
        self.assertEqual(ServiceCategory.objects.filter(value=old_value).count(), 0)

        category = ServiceCategory.objects.filter(value=new_value)
        self.assertEqual(category.count(), 1)
        self.assertEqual(category.first().value, new_value)
        self.assertEqual(category.first().label, new_label)

        # ET les besoins aussi
        self.assertEqual(
            ServiceSubCategory.objects.filter(value=old_subcategory_value_1).count(), 0
        )
        self.assertEqual(
            ServiceSubCategory.objects.filter(value=old_subcategory_value_2).count(), 0
        )
        self.assertEqual(
            ServiceSubCategory.objects.filter(value=new_subcategory_value_1).count(), 1
        )
        self.assertEqual(
            ServiceSubCategory.objects.filter(value=new_subcategory_value_2).count(), 1
        )

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
