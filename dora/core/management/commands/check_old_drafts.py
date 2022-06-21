from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

# from dora.core.emails import send_draft_reminder_email
from dora.services.models import Service, ServiceStatus


class Command(BaseCommand):
    help = "Mass-send user invitations"

    def handle(self, *args, **options):
        drafts = Service.objects.filter(
            status=ServiceStatus.DRAFT,
            creation_date__lte=timezone.now() - timedelta(days=7),
        )
        print(drafts)
        # send_draft_reminder_email(
        #     "cedric.rossi@beta.gouv.fr", "cedric", drafts[0].structure, drafts[0:10]
        # )
