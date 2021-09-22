from model_bakery import baker
from rest_framework.test import APITestCase

from dora.structures.models import Structure

DUMMY_STRUCTURE = {
    "siret": "12345678901234",
    "typology": "PE",
    "name": "Ma structure",
    "short_desc": "Description courte",
    "postal_code": "75001",
    "city": "Paris",
    "address1": "5, avenue de la République",
}


class StructureTestCase(APITestCase):
    def setUp(self):
        self.me = baker.make("users.User")
        self.superuser = baker.make("users.User", is_staff=True)
        self.my_struct = baker.make("Structure")
        self.my_struct.members.add(self.me)

        self.my_other_struct = baker.make("Structure", creator=None, last_editor=None)
        self.my_other_struct.members.add(self.me)

        self.other_struct = baker.make("Structure")
        self.client.force_authenticate(user=self.me)

    # Visibility

    def test_can_see_my_struct(self):
        response = self.client.get("/structures/")
        structures_ids = [s["slug"] for s in response.data]
        self.assertIn(self.my_struct.slug, structures_ids)
        self.assertIn(self.my_other_struct.slug, structures_ids)

    def test_can_see_others_struct(self):
        response = self.client.get("/structures/")
        structures_ids = [s["slug"] for s in response.data]
        self.assertIn(self.other_struct.slug, structures_ids)

    # Modification

    def test_can_edit_my_structures(self):
        response = self.client.patch(
            f"/structures/{self.my_struct.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/structures/{self.my_struct.slug}/")
        self.assertEqual(response.data["name"], "xxx")

    def test_cant_edit_others_structures(self):
        response = self.client.patch(
            f"/structures/{self.other_struct.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 403)

    def test_edit_structures_updates_last_editor(self):
        response = self.client.patch(
            f"/structures/{self.my_other_struct.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 200)
        slug = response.data["slug"]
        s = Structure.objects.get(slug=slug)
        self.assertEqual(s.last_editor, self.me)

    # Superuser

    def test_superuser_can_sees_everything(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get("/structures/")
        services_ids = [s["slug"] for s in response.data]
        self.assertIn(self.my_struct.slug, services_ids)
        self.assertIn(self.my_other_struct.slug, services_ids)
        self.assertIn(self.other_struct.slug, services_ids)

    def test_superuser_can_edit_everything(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.patch(
            f"/structures/{self.my_struct.slug}/", {"name": "xxx"}
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/structures/{self.my_struct.slug}/")
        self.assertEqual(response.data["name"], "xxx")

    # Adding

    def test_can_add_structure(self):
        response = self.client.post(
            "/structures/",
            DUMMY_STRUCTURE,
        )
        self.assertEqual(response.status_code, 201)
        slug = response.data["slug"]
        Structure.objects.get(slug=slug)

    def test_adding_structure_populates_creator_last_editor(self):
        response = self.client.post(
            "/structures/",
            DUMMY_STRUCTURE,
        )
        self.assertEqual(response.status_code, 201)
        slug = response.data["slug"]
        new_structure = Structure.objects.get(slug=slug)
        self.assertEqual(new_structure.creator, self.me)
        self.assertEqual(new_structure.last_editor, self.me)

    # Test structure creation/joining; maybe in rest_auth app?
    # Need to mock email sending
    # def test_adding_structure_creates_membership(self):
    #     self.assertTrue(False)

    # def test_adding_structure_makes_admin(self):
    #     self.assertTrue(False)

    # def test_join_structure_makes_nonadmin(self):
    #     self.assertTrue(False)

    # Deleting

    def test_cant_delete_structure(self):
        response = self.client.delete(
            f"/structures/{self.my_struct.slug}/",
        )
        self.assertEqual(response.status_code, 403)
