from datetime import timedelta

from django.utils import timezone
from dora.structures.models import StructureMember
from model_bakery import baker
from rest_framework.test import APITestCase, APITransactionTestCase

from dora.core.test_utils import make_structure
from dora.services.enums import ServiceStatus

from .models import ServiceSuggestion

DUMMY_SUGGESTION = {
    "name": "Mon service",
    "siret": "12345678901234",
    "contents": {"short_desc": "Lorem Ipsum"},
}


class ServiceSuggestionsTransactionTestCase(APITransactionTestCase):
    def setUp(self):
        baker.make("Establishment", siret=DUMMY_SUGGESTION["siret"])

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
        baker.make("StructureSource", value="suggestion-collaborative")
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        response = self.client.post("/services-suggestions/", DUMMY_SUGGESTION)
        self.assertEqual(response.status_code, 201)

        db_obj = ServiceSuggestion.objects.all()[0]
        self.assertEqual(db_obj.creator.email, user.email)


class ServiceSuggestionsTestCase(APITestCase):
    def setUp(self):
        baker.make("Establishment", siret=DUMMY_SUGGESTION["siret"])

    # NO ACCESS ANONYMOUS
    def test_cant_get_suggestion_anonymously(self):
        suggestion = baker.make(ServiceSuggestion)
        response = self.client.get(f"/services-suggestions/{suggestion.id}/")
        self.assertEqual(response.status_code, 401)

    def test_cant_modify_suggestion_anonymously(self):
        suggestion = baker.make(ServiceSuggestion)
        response = self.client.put(
            f"/services-suggestions/{suggestion.id}/", {"name": "new_name"}
        )
        self.assertEqual(response.status_code, 401)

    def test_cant_delete_suggestion_anonymously(self):
        suggestion = baker.make(ServiceSuggestion)
        response = self.client.delete(f"/services-suggestions/{suggestion.id}/")
        self.assertEqual(response.status_code, 401)

    def test_cant_list_suggestions_anonymously(self):
        baker.make(ServiceSuggestion)
        response = self.client.get("/services-suggestions/")
        self.assertEqual(response.status_code, 401)

    # NO ACCESS LOGGED
    def test_cant_get_suggestion_auth(self):
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        suggestion = baker.make(ServiceSuggestion)
        response = self.client.get(f"/services-suggestions/{suggestion.id}/")
        self.assertEqual(response.status_code, 403)

    def test_cant_modify_suggestion_auth(self):
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        suggestion = baker.make(ServiceSuggestion)
        response = self.client.put(
            f"/services-suggestions/{suggestion.id}/", {"name": "new_name"}
        )
        self.assertEqual(response.status_code, 403)

    def test_cant_delete_suggestion_auth(self):
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        suggestion = baker.make(ServiceSuggestion)
        response = self.client.delete(f"/services-suggestions/{suggestion.id}/")
        self.assertEqual(response.status_code, 403)

    def test_cant_list_suggestions_auth(self):
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        baker.make(ServiceSuggestion)
        response = self.client.get("/services-suggestions/")
        self.assertEqual(response.status_code, 403)

    # TEAM MODERATION
    def test_bizdev_can_reject(self):
        suggestion = baker.make("ServiceSuggestion")
        user = baker.make("users.User", is_valid=True, is_bizdev=True)
        self.client.force_authenticate(user=user)
        response = self.client.delete(f"/services-suggestions/{suggestion.id}/")
        self.assertEqual(response.status_code, 204)

    def test_su_can_reject(self):
        suggestion = baker.make("ServiceSuggestion")
        user = baker.make("users.User", is_valid=True, is_staff=True)
        self.client.force_authenticate(user=user)
        response = self.client.delete(f"/services-suggestions/{suggestion.id}/")
        self.assertEqual(response.status_code, 204)

    def test_anon_cant_reject(self):
        suggestion = baker.make("ServiceSuggestion")
        response = self.client.delete(f"/services-suggestions/{suggestion.id}/")
        self.assertEqual(response.status_code, 401)

    def test_user_cant_reject(self):
        suggestion = baker.make("ServiceSuggestion")
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        response = self.client.delete(f"/services-suggestions/{suggestion.id}/")
        self.assertEqual(response.status_code, 403)

    def test_bizdev_can_accept(self):
        suggestion = baker.make("ServiceSuggestion", siret=DUMMY_SUGGESTION["siret"])
        user = baker.make("users.User", is_valid=True, is_bizdev=True)
        self.client.force_authenticate(user=user)
        response = self.client.post(f"/services-suggestions/{suggestion.id}/validate/")
        self.assertEqual(response.status_code, 201)

    def test_su_can_accept(self):
        suggestion = baker.make("ServiceSuggestion", siret=DUMMY_SUGGESTION["siret"])
        user = baker.make("users.User", is_valid=True, is_staff=True)
        self.client.force_authenticate(user=user)
        response = self.client.post(f"/services-suggestions/{suggestion.id}/validate/")
        self.assertEqual(response.status_code, 201)

    def test_anon_cant_accept(self):
        suggestion = baker.make("ServiceSuggestion", siret=DUMMY_SUGGESTION["siret"])
        response = self.client.post(f"/services-suggestions/{suggestion.id}/validate/")
        self.assertEqual(response.status_code, 401)

    def test_user_cant_accept(self):
        suggestion = baker.make("ServiceSuggestion", siret=DUMMY_SUGGESTION["siret"])
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        response = self.client.post(f"/services-suggestions/{suggestion.id}/validate/")
        self.assertEqual(response.status_code, 403)

    # Corrects mails contacted when validate
    def test_no_mail_send(self):
        # ÉTANT DONNÉ une suggestion sans email de contact et sans structure associée
        suggestion = baker.make("ServiceSuggestion", siret=DUMMY_SUGGESTION["siret"])
        user = baker.make("users.User", is_valid=True, is_bizdev=True)
        self.client.force_authenticate(user=user)

        # QUAND je valide cette suggestion
        response = self.client.post(f"/services-suggestions/{suggestion.id}/validate/")

        # ALORS aucune personne n'est contacté
        self.assertEqual(response.data["emails_contacted"], [])
        self.assertEqual(response.status_code, 201)

    def test_mail_send_to_contact_email(self):
        # ÉTANT DONNÉ une suggestion avec email de contact et sans structure associée
        email = "mail@mail.fr"
        suggestion = baker.make(
            "ServiceSuggestion",
            siret=DUMMY_SUGGESTION["siret"],
            contents={"contact_email": email},
        )
        user = baker.make("users.User", is_valid=True, is_bizdev=True)
        self.client.force_authenticate(user=user)

        # QUAND je valide cette suggestion
        response = self.client.post(f"/services-suggestions/{suggestion.id}/validate/")

        # ALORS la personne en contact est contacté
        self.assertEqual(response.data["emails_contacted"], [email])
        self.assertEqual(response.status_code, 201)

    def test_mail_send_to_structure_admin(self):
        # ÉTANT DONNÉ une structure avec un administrateur
        admin_mail = "admin@mail.fr"
        admin_user = baker.make("users.User", is_valid=True, email=admin_mail)
        structure = baker.make(
            "Structure", siret=DUMMY_SUGGESTION["siret"], creator=admin_user
        )
        baker.make(StructureMember, structure=structure, user=admin_user, is_admin=True)

        # et une suggestion de service pour cette structure mais sans email de contact
        suggestion = baker.make(
            "ServiceSuggestion",
            siret=DUMMY_SUGGESTION["siret"],
        )

        # QUAND je valide cette suggestion
        bizdev_user = baker.make("users.User", is_valid=True, is_bizdev=True)
        self.client.force_authenticate(user=bizdev_user)
        response = self.client.post(f"/services-suggestions/{suggestion.id}/validate/")

        # ALORS la personne en contact est contacté
        self.assertEqual(response.data["emails_contacted"], [admin_mail])
        self.assertEqual(response.status_code, 201)

    def test_mail_send_to_structure_admin_and_contact_email(self):
        # ÉTANT DONNÉ une structure avec un administrateur
        admin_mail = "admin@mail.fr"
        contact_mail = "mail@mail.fr"
        admin_user = baker.make("users.User", is_valid=True, email=admin_mail)
        structure = baker.make(
            "Structure", siret=DUMMY_SUGGESTION["siret"], creator=admin_user
        )
        baker.make(StructureMember, structure=structure, user=admin_user, is_admin=True)

        # et une suggestion de service pour cette structure mais sans email de contact
        suggestion = baker.make(
            "ServiceSuggestion",
            siret=DUMMY_SUGGESTION["siret"],
            contents={"contact_email": contact_mail},
        )

        # QUAND je valide cette suggestion
        bizdev_user = baker.make("users.User", is_valid=True, is_bizdev=True)
        self.client.force_authenticate(user=bizdev_user)
        response = self.client.post(f"/services-suggestions/{suggestion.id}/validate/")

        # ALORS la personne en contact est contacté
        self.assertEqual(
            response.data["emails_contacted"],
            [admin_mail, contact_mail],
        )
        self.assertEqual(response.status_code, 201)

    # Validated services visibility
    def test_member_can_see_suggested_service(self):
        structure = make_structure()
        service = baker.make(
            "Service", structure=structure, status=ServiceStatus.SUGGESTION
        )
        user = baker.make("users.User", is_valid=True)
        structure.members.add(user)
        self.client.force_authenticate(user=user)
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 200)

    def test_su_can_see_suggested_service(self):
        structure = make_structure()
        service = baker.make(
            "Service", structure=structure, status=ServiceStatus.SUGGESTION
        )
        user = baker.make("users.User", is_valid=True, is_staff=True)
        self.client.force_authenticate(user=user)
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 200)

    def test_anon_cant_see_suggested_service(self):
        structure = make_structure()
        service = baker.make(
            "Service", structure=structure, status=ServiceStatus.SUGGESTION
        )
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 404)

    def test_user_cant_see_suggested_service(self):
        structure = make_structure()
        service = baker.make(
            "Service", structure=structure, status=ServiceStatus.SUGGESTION
        )
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        response = self.client.get(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 404)

    # STRUCTURE MODERATION
    def test_member_can_delete(self):
        structure = make_structure()
        service = baker.make(
            "Service", structure=structure, status=ServiceStatus.SUGGESTION
        )
        user = baker.make("users.User", is_valid=True)
        structure.members.add(user)
        self.client.force_authenticate(user=user)
        response = self.client.delete(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 204)

    def test_su_can_delete(self):
        structure = make_structure()
        service = baker.make(
            "Service", structure=structure, status=ServiceStatus.SUGGESTION
        )
        user = baker.make("users.User", is_valid=True, is_staff=True)
        self.client.force_authenticate(user=user)
        response = self.client.delete(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 204)

    def test_anon_cant_delete(self):
        structure = make_structure()
        service = baker.make(
            "Service", structure=structure, status=ServiceStatus.SUGGESTION
        )
        response = self.client.delete(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 401)

    def test_user_cant_delete(self):
        structure = make_structure()
        service = baker.make(
            "Service", structure=structure, status=ServiceStatus.SUGGESTION
        )
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        response = self.client.delete(f"/services/{service.slug}/")
        self.assertEqual(response.status_code, 404)

    def test_member_can_convert_to_draft(self):
        structure = make_structure()
        service = baker.make(
            "Service", structure=structure, status=ServiceStatus.SUGGESTION
        )
        user = baker.make("users.User", is_valid=True)
        structure.members.add(user)
        self.client.force_authenticate(user=user)
        response = self.client.patch(
            f"/services/{service.slug}/", status=ServiceStatus.DRAFT
        )
        self.assertEqual(response.status_code, 200)

    def test_su_can_convert_to_draft(self):
        structure = make_structure()
        service = baker.make(
            "Service", structure=structure, status=ServiceStatus.SUGGESTION
        )
        user = baker.make("users.User", is_valid=True, is_staff=True)
        self.client.force_authenticate(user=user)
        response = self.client.patch(
            f"/services/{service.slug}/", status=ServiceStatus.DRAFT
        )
        self.assertEqual(response.status_code, 200)

    def test_anon_cant_convert_to_draft(self):
        structure = make_structure()
        service = baker.make(
            "Service", structure=structure, status=ServiceStatus.SUGGESTION
        )
        response = self.client.patch(
            f"/services/{service.slug}/", status=ServiceStatus.DRAFT
        )
        self.assertEqual(response.status_code, 401)

    def test_user_cant_convert_to_draft(self):
        structure = make_structure()
        service = baker.make(
            "Service", structure=structure, status=ServiceStatus.SUGGESTION
        )
        user = baker.make("users.User", is_valid=True)
        self.client.force_authenticate(user=user)
        response = self.client.patch(
            f"/services/{service.slug}/", status=ServiceStatus.DRAFT
        )
        self.assertEqual(response.status_code, 404)
