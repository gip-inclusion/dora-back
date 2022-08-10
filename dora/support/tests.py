from model_bakery import baker
from rest_framework.test import APITestCase

from dora.core.test_utils import make_service, make_structure
from dora.services.enums import ServiceStatus


class SupportTestCase(APITestCase):
    def setUp(self):
        self.staff = baker.make("users.User", is_valid=True, is_staff=True)
        self.nonstaff = baker.make("users.User", is_valid=True, is_staff=False)

    def test_staff_can_see_service_list(self):
        service = make_service(status=ServiceStatus.PUBLISHED)
        self.client.force_authenticate(user=self.staff)
        response = self.client.get("/services-admin/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["slug"], service.slug)

    def test_staff_can_see_service(self):
        service = make_service(status=ServiceStatus.PUBLISHED)
        self.client.force_authenticate(user=self.staff)
        response = self.client.get(f"/services-admin/{service.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["slug"], service.slug)

    def test_nonstaff_cant_see_service_list(self):
        make_service(status=ServiceStatus.PUBLISHED)
        self.client.force_authenticate(user=self.nonstaff)
        response = self.client.get("/services-admin/")
        self.assertEqual(response.status_code, 403)

    def test_nonstaff_cant_see_service(self):
        service = make_service(status=ServiceStatus.PUBLISHED)
        self.client.force_authenticate(user=self.nonstaff)
        response = self.client.get(f"/services-admin/{service.slug}/")
        self.assertEqual(response.status_code, 403)

    def test_anon_cant_see_service_list(self):
        make_service(status=ServiceStatus.PUBLISHED)
        response = self.client.get("/services-admin/")
        self.assertEqual(response.status_code, 401)

    def test_anon_cant_see_service(self):
        service = make_service(status=ServiceStatus.PUBLISHED)
        response = self.client.get(f"/services-admin/{service.slug}/")
        self.assertEqual(response.status_code, 401)

    def test_staff_cant_see_drafts(self):
        service = make_service(status=ServiceStatus.DRAFT)
        self.client.force_authenticate(user=self.staff)
        response = self.client.get(f"/services-admin/{service.slug}/")
        self.assertEqual(response.status_code, 404)

    def test_staff_cant_see_archive(self):
        service = make_service(status=ServiceStatus.ARCHIVED)
        self.client.force_authenticate(user=self.staff)
        response = self.client.get(f"/services-admin/{service.slug}/")
        self.assertEqual(response.status_code, 404)

    def test_staff_can_see_structure_list(self):
        structure = make_structure()
        self.client.force_authenticate(user=self.staff)
        response = self.client.get("/structures-admin/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["slug"], structure.slug)

    def test_staff_can_see_structure(self):
        structure = make_structure()
        self.client.force_authenticate(user=self.staff)
        response = self.client.get(f"/structures-admin/{structure.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["slug"], structure.slug)

    def test_nonstaff_cant_see_structure_list(self):
        make_structure()
        self.client.force_authenticate(user=self.nonstaff)
        response = self.client.get("/structures-admin/")
        self.assertEqual(response.status_code, 403)

    def test_nonstaff_cant_see_structure(self):
        structure = make_structure()
        self.client.force_authenticate(user=self.nonstaff)
        response = self.client.get(f"/structures-admin/{structure.slug}/")
        self.assertEqual(response.status_code, 403)

    def test_anon_cant_see_structure_list(self):
        make_structure()
        response = self.client.get("/structures-admin/")
        self.assertEqual(response.status_code, 401)

    def test_anon_cant_see_structure(self):
        structure = make_structure()
        response = self.client.get(f"/structures-admin/{structure.slug}/")
        self.assertEqual(response.status_code, 401)
