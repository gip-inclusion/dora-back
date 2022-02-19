from model_bakery import baker
from rest_framework.test import APITestCase


class UserTestCase(APITestCase):
    def setUp(self):
        self.user = baker.make("users.User", is_valid=True)

    # Profile update
    def test_anonymous_cant_change_profile(self):
        response = self.client.post(
            "/profile/change/",
            {
                "first_name": "xxx",
                "last_name": "yyy",
                "phone_number": "1234",
                "newsletter": True,
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_can_change_profile(self):
        self.client.force_authenticate(user=self.user)
        self.assertFalse(
            self.user.newsletter,
        )
        new_data = {
            "first_name": "xxx",
            "last_name": "yyy",
            "phone_number": "1234",
            "newsletter": True,
        }
        response = self.client.post(
            "/profile/change/",
            new_data,
        )
        self.assertEqual(response.status_code, 200)
        # test response content
        for attr, value in new_data.items():
            self.assertEqual(response.data[attr], value)
        # test user content
        self.user.refresh_from_db()
        for attr, value in new_data.items():
            self.assertEqual(getattr(self.user, attr), value)

    def test_can_do_partial_profile_update(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/profile/change/",
            {
                "first_name": "xxx",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["first_name"], "xxx")
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "xxx")

    def test_cant_change_email(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/profile/change/",
            {
                "email": "xxx@test.com",
            },
        )
        self.assertEqual(response.status_code, 400)

    # Password change
    def test_anonymous_cant_change_passworc(self):
        response = self.client.post(
            "/profile/password/change/",
            {
                "current_password": "password",
                "new_password": "MyNewPassword1234",
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_can_change_password(self):
        # Force a known password
        self.user.set_password("password")
        self.user.save()
        self.client.force_authenticate(user=self.user)

        new_data = {
            "current_password": "password",
            "new_password": "MyNewPassword1234",
        }
        response = self.client.post(
            "/profile/password/change/",
            new_data,
        )
        self.assertEqual(response.status_code, 204)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("MyNewPassword1234"))

    def test_must_know_current_password_to_change_it(self):
        # Force a known password
        self.user.set_password("password")
        self.user.save()
        self.client.force_authenticate(user=self.user)

        new_data = {
            "current_password": "xxxx",
            "new_password": "MyNewPassword1234",
        }
        response = self.client.post(
            "/profile/password/change/",
            new_data,
        )
        self.assertEqual(response.status_code, 403)
