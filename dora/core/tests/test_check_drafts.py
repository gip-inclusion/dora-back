from datetime import timedelta

from django.core import mail
from django.core.management import call_command
from django.utils import timezone
from freezegun import freeze_time
from model_bakery import baker
from rest_framework.test import APITestCase

from dora.core.test_utils import make_service, make_structure
from dora.services.enums import ServiceStatus


class CheckDraftsTestCase(APITestCase):
    def setUp(self):
        self.me = baker.make("users.User", is_valid=True)
        self.somebody = baker.make("users.User", is_valid=True)
        self.superuser = baker.make("users.User", is_staff=True, is_valid=True)
        self.my_struct = make_structure(self.me)

    def call_command(self):
        call_command("check_old_drafts")

    def test_draft_older_than_7_days_notified(self):
        with freeze_time(timezone.now() - timedelta(days=8)):
            service = make_service(
                status=ServiceStatus.DRAFT,
                creator=self.me,
                last_draft_notification_date=None,
            )
        self.call_command()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Besoin d'aide", mail.outbox[0].subject)
        self.assertIn(service.slug, mail.outbox[0].body)
        self.assertIn(self.me.email, mail.outbox[0].to)

    def test_draft_newer_than_7_days_not_notified(self):
        with freeze_time(timezone.now() - timedelta(days=6)):
            make_service(
                status=ServiceStatus.DRAFT,
                creator=self.me,
                last_draft_notification_date=None,
            )
        self.call_command()
        self.assertEqual(len(mail.outbox), 0)

    def test_notif_sent_only_once(self):
        with freeze_time(timezone.now() - timedelta(days=8)):
            make_service(
                status=ServiceStatus.DRAFT,
                creator=self.me,
                last_draft_notification_date=None,
            )
        self.call_command()
        self.assertEqual(len(mail.outbox), 1)
        mail.outbox = []
        self.call_command()
        self.assertEqual(len(mail.outbox), 0)

    def test_notif_sent_editor_creator(self):
        with freeze_time(timezone.now() - timedelta(days=8)):
            make_service(
                status=ServiceStatus.DRAFT,
                creator=self.me,
                last_editor=self.somebody,
                last_draft_notification_date=None,
            )
        self.call_command()
        self.assertEqual(len(mail.outbox), 2)
        self.assertTrue(self.me.email in [*mail.outbox[0].to, *mail.outbox[1].to])
        self.assertTrue(self.somebody.email in [*mail.outbox[0].to, *mail.outbox[1].to])

    def test_notif_only_once_same_editor_creator(self):
        with freeze_time(timezone.now() - timedelta(days=8)):
            make_service(
                status=ServiceStatus.DRAFT,
                creator=self.me,
                last_editor=self.me,
                last_draft_notification_date=None,
            )
        self.call_command()
        self.assertEqual(len(mail.outbox), 1)

    def test_notdraft_older_than_7_days_not_notified(self):
        with freeze_time(timezone.now() - timedelta(days=8)):
            service = make_service(
                status=ServiceStatus.DRAFT,
                creator=self.me,
                last_draft_notification_date=None,
            )
        with freeze_time(timezone.now() - timedelta(days=4)):
            service.status = ServiceStatus.PUBLISHED
            service.save()
        self.call_command()
        self.assertEqual(len(mail.outbox), 0)
