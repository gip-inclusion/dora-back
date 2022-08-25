from datetime import timedelta
from io import StringIO

from django.core import mail
from django.core.management import call_command
from django.utils import timezone
from freezegun import freeze_time
from model_bakery import baker
from rest_framework.test import APITestCase

from dora.core.test_utils import make_service, make_structure
from dora.services.enums import ServiceStatus
from dora.structures.models import StructureMember


class ServiceUpdateNotificationTestCase(APITestCase):
    def call_command(self):
        call_command("service_update_notification", stdout=StringIO())

    def test_no_service(self):
        # ÉTANT DONNÉ aucun service

        # QUAND j'appelle la commande de rappel d'actualisation
        self.call_command()

        # ALORS aucun courriel n'est envoyé
        self.assertEqual(len(mail.outbox), 0)

    def test_no_mails_for_service_recently_updated(self):
        # ÉTANT DONNÉ un service mis à jour récemment
        structure = make_structure(name="My Structure")

        with freeze_time(timezone.now() - timedelta(days=1)):
            make_service(
                structure=structure,
                status=ServiceStatus.PUBLISHED,
            )

        # QUAND j'appelle la commande de rappel d'actualisation
        self.call_command()

        # ALORS aucun courriel n'est envoyé
        self.assertEqual(len(mail.outbox), 0)

    def test_no_mails_for_old_service_related_to_one_structure_without_admin(self):
        # ÉTANT DONNÉ un service nécessitant une mise à jour
        # relié à une structure sans admin
        structure = make_structure(name="My Structure")
        with freeze_time(timezone.now() - timedelta(days=300)):
            make_service(
                structure=structure,
                status=ServiceStatus.PUBLISHED,
            )

        # QUAND j'appelle la commande de rappel d'actualisation
        self.call_command()

        # ALORS aucun courriel n'est envoyé
        self.assertEqual(len(mail.outbox), 0)

    def test_mails_for_old_service_related_to_one_structure(self):
        # ÉTANT DONNÉ un service nécessitant une mise à jour
        # relié à une structure avec un admin
        admin_mail = "admin@example.com"
        admin_user = baker.make("users.User", is_valid=True, email=admin_mail)
        service_name = "My service"

        structure = make_structure(name="My Structure")
        baker.make(StructureMember, structure=structure, user=admin_user, is_admin=True)
        with freeze_time(timezone.now() - timedelta(days=300)):
            make_service(
                name=service_name,
                structure=structure,
                status=ServiceStatus.PUBLISHED,
            )

        # QUAND j'appelle la commande de rappel d'actualisation
        self.call_command()

        # ALORS un courriel est envoyé au responsable de la structure
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("[DORA] Actualisation de services", mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, [admin_mail])
        self.assertIn(service_name, mail.outbox[0].body)

    def test_mails_for_old_service_related_to_one_structure_two_admins(self):
        # ÉTANT DONNÉ un service nécessitant une mise à jour
        # relié à une structure avec deux admins
        admin_mail_1 = "admin1@example.com"
        admin_mail_2 = "admin2@example.com"
        admin_user_1 = baker.make("users.User", is_valid=True, email=admin_mail_1)
        admin_user_2 = baker.make("users.User", is_valid=True, email=admin_mail_2)
        service_name = "My service"

        structure = make_structure(name="My Structure")
        baker.make(
            StructureMember, structure=structure, user=admin_user_1, is_admin=True
        )
        baker.make(
            StructureMember, structure=structure, user=admin_user_2, is_admin=True
        )
        with freeze_time(timezone.now() - timedelta(days=300)):
            make_service(
                name=service_name,
                structure=structure,
                status=ServiceStatus.PUBLISHED,
            )

        # QUAND j'appelle la commande de rappel d'actualisation
        self.call_command()

        # ALORS un courriel est envoyé aux deux responsables de la structure
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("[DORA] Actualisation de services", mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, [admin_mail_1, admin_mail_2])
        self.assertIn(service_name, mail.outbox[0].body)

    def test_mails_for_two_services_related_to_one_structure(self):
        # ÉTANT DONNÉ deux services dont seul un nécessite une mise à jour
        # relié à une structure avec un admin
        admin_mail = "admin@example.com"
        admin_user = baker.make("users.User", is_valid=True, email=admin_mail)
        service_name_1 = "My service 1"
        service_name_2 = "My service 2"

        structure = make_structure(name="My Structure")
        baker.make(StructureMember, structure=structure, user=admin_user, is_admin=True)
        with freeze_time(timezone.now() - timedelta(days=300)):
            make_service(
                name=service_name_1,
                structure=structure,
                status=ServiceStatus.PUBLISHED,
            )
        with freeze_time(timezone.now() - timedelta(days=3)):
            make_service(
                name=service_name_2,
                structure=structure,
                status=ServiceStatus.PUBLISHED,
            )

        # QUAND j'appelle la commande de rappel d'actualisation
        self.call_command()

        # ALORS un courriel est envoyé au responsable de la structure avec seulement un service
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("[DORA] Actualisation de services", mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, [admin_mail])
        self.assertIn(service_name_1, mail.outbox[0].body)
        self.assertNotIn(service_name_2, mail.outbox[0].body)

    def test_mails_for_two_services_related_to_two_structure(self):
        # ÉTANT DONNÉ un service nécessitant une mise à jour
        # relié à une structure avec un admin
        struct_1_admin_mail = "admin@example.com"
        admin_user = baker.make("users.User", is_valid=True, email=struct_1_admin_mail)
        service_name_1 = "Struct 1 - My service"
        structure = make_structure(name="My Structure")
        baker.make(StructureMember, structure=structure, user=admin_user, is_admin=True)

        with freeze_time(timezone.now() - timedelta(days=300)):
            make_service(
                name=service_name_1,
                structure=structure,
                status=ServiceStatus.PUBLISHED,
            )

        # ET un second service ne nécessitant pas de mise à jour
        # relié à une structure avec un admin
        struct_2_admin_mail = "admin2@example.com"
        admin_user_2 = baker.make(
            "users.User", is_valid=True, email=struct_2_admin_mail
        )
        service_name_2 = "Struct 2 - My service"
        structure_2 = make_structure(name="My Structure 2")
        baker.make(
            StructureMember, structure=structure_2, user=admin_user_2, is_admin=True
        )
        with freeze_time(timezone.now() - timedelta(days=30)):
            make_service(
                name=service_name_2,
                structure=structure_2,
                status=ServiceStatus.PUBLISHED,
            )

        # QUAND j'appelle la commande de rappel d'actualisation
        self.call_command()

        # ALORS un courriel est envoyé au responsable de la structure 1
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("[DORA] Actualisation de services", mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, [struct_1_admin_mail])
        self.assertIn(service_name_1, mail.outbox[0].body)
        self.assertNotIn(service_name_2, mail.outbox[0].body)

    def test_mails_for_two_old_services_related_to_two_structure(self):
        # ÉTANT DONNÉ un service nécessitant une mise à jour
        # relié à une structure avec un admin
        struct_1_admin_mail = "admin@example.com"
        admin_user = baker.make("users.User", is_valid=True, email=struct_1_admin_mail)
        service_name_1 = "Struct 1 - My service"
        structure = make_structure(name="My Structure")
        baker.make(StructureMember, structure=structure, user=admin_user, is_admin=True)

        with freeze_time(timezone.now() - timedelta(days=300)):
            make_service(
                name=service_name_1,
                structure=structure,
                status=ServiceStatus.PUBLISHED,
            )

        # ET un second service nécessitant lui aussi une mise à jour
        # relié à une structure avec un admin
        struct_2_admin_mail = "admin2@example.com"
        admin_user_2 = baker.make(
            "users.User", is_valid=True, email=struct_2_admin_mail
        )
        service_name_2 = "Struct 2 - My service"
        structure_2 = make_structure(name="My Structure 2")
        baker.make(
            StructureMember, structure=structure_2, user=admin_user_2, is_admin=True
        )
        with freeze_time(timezone.now() - timedelta(days=450)):
            make_service(
                name=service_name_2,
                structure=structure_2,
                status=ServiceStatus.PUBLISHED,
            )

        # QUAND j'appelle la commande de rappel d'actualisation
        self.call_command()

        # ALORS deux courriels sont envoyé aux responsable des deux structures
        self.assertEqual(len(mail.outbox), 2)

        mail_1 = mail.outbox[0]
        self.assertIn("[DORA] Actualisation de services", mail_1.subject)
        self.assertEqual(mail_1.to, [struct_1_admin_mail])
        self.assertIn(service_name_1, mail_1.body)
        self.assertNotIn(service_name_2, mail_1.body)

        mail_2 = mail.outbox[1]
        self.assertIn("[DORA] Actualisation de services", mail_2.subject)
        self.assertEqual(mail_2.to, [struct_2_admin_mail])
        self.assertIn(service_name_2, mail_2.body)
        self.assertNotIn(service_name_1, mail_2.body)

    def test_mails_for_three_old_services_related_to_two_structure(self):
        # ÉTANT DONNÉ un service nécessitant une mise à jour
        # avec un second récemment modifié
        # relié à une structure avec un admin
        struct_1_admin_mail = "admin@example.com"
        admin_user = baker.make("users.User", is_valid=True, email=struct_1_admin_mail)
        service_name_1_1 = "Struct 1-1 - My service"
        service_name_1_2 = "Struct 1-2 - My service"
        structure = make_structure(name="My Structure")
        baker.make(StructureMember, structure=structure, user=admin_user, is_admin=True)
        with freeze_time(timezone.now() - timedelta(days=300)):
            make_service(
                name=service_name_1_1,
                structure=structure,
                status=ServiceStatus.PUBLISHED,
            )
        with freeze_time(timezone.now() - timedelta(days=30)):
            make_service(
                name=service_name_1_2,
                structure=structure,
                status=ServiceStatus.PUBLISHED,
            )

        # ET un second service nécessitant lui aussi une mise à jour
        # relié à une structure avec un admin
        struct_2_admin_mail = "admin2@example.com"
        admin_user_2 = baker.make(
            "users.User", is_valid=True, email=struct_2_admin_mail
        )
        service_name_2 = "Struct 2 - My service"
        structure_2 = make_structure(name="My Structure 2")
        baker.make(
            StructureMember, structure=structure_2, user=admin_user_2, is_admin=True
        )
        with freeze_time(timezone.now() - timedelta(days=450)):
            make_service(
                name=service_name_2,
                structure=structure_2,
                status=ServiceStatus.PUBLISHED,
            )

        # QUAND j'appelle la commande de rappel d'actualisation
        self.call_command()

        # ALORS deux courriels sont envoyé aux responsable des deux structures
        self.assertEqual(len(mail.outbox), 2)

        mail_1 = mail.outbox[0]
        self.assertIn("[DORA] Actualisation de services", mail_1.subject)
        self.assertEqual(mail_1.to, [struct_1_admin_mail])
        self.assertIn(service_name_1_1, mail_1.body)
        self.assertNotIn(service_name_1_2, mail_1.body)
        self.assertNotIn(service_name_2, mail_1.body)

        mail_2 = mail.outbox[1]
        self.assertIn("[DORA] Actualisation de services", mail_2.subject)
        self.assertEqual(mail_2.to, [struct_2_admin_mail])
        self.assertIn(service_name_2, mail_2.body)
        self.assertNotIn(service_name_1_1, mail_2.body)
        self.assertNotIn(service_name_1_2, mail_2.body)
