from model_bakery import baker
from rest_framework.test import APITestCase

from dora.core.test_utils import make_service

from ..models import Bookmark


class ServiceBookmarkTestCase(APITestCase):
    def test_add_bookmark(self):
        self.assertEqual(Bookmark.objects.count(), 0)
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        service = make_service()

        response = self.client.post("/bookmarks/", {"slug": service.slug})
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Bookmark.objects.count(), 1)

        bookmark = Bookmark.objects.get(di_id="di-123456789")
        self.assertEqual(bookmark.slug, service.slug)
        self.assertEqual(bookmark.service_id, service.id)
        self.assertEqual(bookmark.di_id, None)

    def test_add_duplicate_bookmark(self):
        self.assertEqual(Bookmark.objects.count(), 0)
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        service = make_service()

        response = self.client.post("/bookmarks/", {"slug": service.slug})
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Bookmark.objects.count(), 1)
        response = self.client.post("/bookmarks/", {"slug": service.slug})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Bookmark.objects.count(), 1)

    def test_add_bookmark_either_service_or_di_id(self):
        assert False

    def test_add_bookmark_either_di_id_or_service(self):
        assert False

    def test_add_di_bookmark(self):
        self.assertEqual(Bookmark.objects.count(), 0)
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)

        response = self.client.post("/bookmarks/", {"di_id": "di-123456789"})
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Bookmark.objects.count(), 1)

        di_bookmark = Bookmark.objects.get(di_id="di-123456789")
        self.assertEqual(di_bookmark.di_id, "di-123456789")
        self.assertEqual(di_bookmark.service_id, None)

    def test_add_duplicate_di_bookmark(self):
        self.assertEqual(Bookmark.objects.count(), 0)
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)

        response = self.client.post("/bookmarks/", {"di_id": "di-123456789"})
        self.assertEqual(Bookmark.objects.count(), 1)

        response = self.client.post("/bookmarks/", {"di_id": "di-123456789"})

        self.assertEqual(response.status_code, 400)  # TODO, should give an error?
        self.assertEqual(Bookmark.objects.count(), 1)

    def test_add_di_bookmark_not_logged_failed(self):
        self.assertEqual(Bookmark.objects.count(), 0)
        response = self.client.post("/bookmarks/", {"di_id": "di-123456789"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(Bookmark.objects.count(), 0)

    def test_remove_di_bookmark(self):
        DI_ID = "di-123456789"
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        baker.make("services.Bookmark", di_id=DI_ID, user=user)
        self.assertEqual(Bookmark.objects.count(), 1)
        response = self.client.delete("/bookmarks/", {"di_id": DI_ID})
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Bookmark.objects.count(), 0)

    def test_remove_bookmark(self):
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        service = baker.make("services.Bookmark", service=make_service(), user=user)
        self.assertEqual(Bookmark.objects.count(), 1)

        response = self.client.delete("/bookmarks/", {"service": service})
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Bookmark.objects.count(), 0)

    def test_cant_remove_somebody_else_bookmark(self):
        assert False
