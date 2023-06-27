from model_bakery import baker
from rest_framework.test import APITestCase


class UserTestCase(APITestCase):
    def setUp(self):
        self.user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=self.user)

    def test_wrong_main_activity(self):
        main_activity = "xxx"
        response = self.client.patch(
            "/profile/update-main-activity/",
            {"main_activity": main_activity},
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotEquals(self.user.main_activity, main_activity)

    def test_main_activity_is_correctly_updated(self):
        main_activity = "offreur"

        response = self.client.patch(
            "/profile/update-main-activity/",
            {"main_activity": main_activity},
        )
        self.user.refresh_from_db()

        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.user.main_activity, main_activity)

    def test_main_activity_is_correctly_updated_but_not_the_first_name(self):
        main_activity = "offreur"
        first_name = "new_first_name"

        response = self.client.patch(
            "/profile/update-main-activity/",
            {"main_activity": main_activity, "first_name": first_name},
        )
        self.user.refresh_from_db()

        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.user.main_activity, main_activity)
        self.assertNotEquals(self.user.first_name, first_name)
