from datetime import timedelta

from django.utils import timezone
from model_bakery import baker
from rest_framework.test import APITestCase

from .models import ServiceSuggestion

DUMMY_SUGGESTION = {
    "name": "Mon service",
    "siret": "12345678901234",
    "contents": "{test: 1}",
}


class ServiceSuggestionsTestCase(APITestCase):
    # CREATION
    def test_can_create_anonymous_suggestion(self):
        db_objs = ServiceSuggestion.objects.all()
        self.assertEqual(db_objs.count(), 0)

        response = self.client.post("/services-suggestions/", DUMMY_SUGGESTION)
        self.assertEqual(response.status_code, 201)

        db_objs = ServiceSuggestion.objects.all()
        self.assertEqual(db_objs.count(), 1)
        db_obj = db_objs[0]
        self.assertEqual(db_obj.name, DUMMY_SUGGESTION["name"])
        self.assertEqual(db_obj.siret, DUMMY_SUGGESTION["siret"])
        self.assertEqual(db_obj.contents, DUMMY_SUGGESTION["contents"])
        self.assertIsNone(db_obj.creator)
        self.assertTrue(timezone.now() - db_obj.creation_date < timedelta(seconds=1))

    def test_can_create_nonanonymous_suggestion(self):
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        response = self.client.post("/services-suggestions/", DUMMY_SUGGESTION)
        self.assertEqual(response.status_code, 201)

        db_obj = ServiceSuggestion.objects.all()[0]
        self.assertEqual(db_obj.creator.email, user.email)

    # NO ACCESS ANONYMOUS
    def test_cant_get_suggestion_anonymously(self):
        suggestion = baker.make(ServiceSuggestion)
        response = self.client.get(
            f"/services-suggestions/{suggestion.id}/", {"name": "new_name"}
        )
        self.assertEqual(response.status_code, 404)

    def test_cant_modify_suggestion_anonymously(self):
        suggestion = baker.make(ServiceSuggestion)
        response = self.client.put(
            f"/services-suggestions/{suggestion.id}/", {"name": "new_name"}
        )
        self.assertEqual(response.status_code, 404)

    def test_cant_delete_suggestion_anonymously(self):
        suggestion = baker.make(ServiceSuggestion)
        response = self.client.delete(
            f"/services-suggestions/{suggestion.id}/", {"name": "new_name"}
        )
        self.assertEqual(response.status_code, 404)

    def test_cant_list_suggestions_anonymously(self):
        baker.make(ServiceSuggestion)
        response = self.client.get("/services-suggestions/", {"name": "new_name"})
        self.assertEqual(response.status_code, 401)

    # NO ACCESS LOGGED
    def test_cant_get_suggestion_auth(self):
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        suggestion = baker.make(ServiceSuggestion)
        response = self.client.get(
            f"/services-suggestions/{suggestion.id}/", {"name": "new_name"}
        )
        self.assertEqual(response.status_code, 404)

    def test_cant_modify_suggestion_auth(self):
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        suggestion = baker.make(ServiceSuggestion)
        response = self.client.put(
            f"/services-suggestions/{suggestion.id}/", {"name": "new_name"}
        )
        self.assertEqual(response.status_code, 404)

    def test_cant_delete_suggestion_auth(self):
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        suggestion = baker.make(ServiceSuggestion)
        response = self.client.delete(
            f"/services-suggestions/{suggestion.id}/", {"name": "new_name"}
        )
        self.assertEqual(response.status_code, 404)

    def test_cant_list_suggestions_auth(self):
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        baker.make(ServiceSuggestion)
        response = self.client.get("/services-suggestions/", {"name": "new_name"})
        self.assertEqual(response.status_code, 403)
