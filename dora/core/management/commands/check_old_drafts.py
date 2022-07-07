from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from dora.core.emails import send_draft_reminder_email
from dora.services.models import Service, ServiceStatus


class Command(BaseCommand):
    help = "Mass-send user invitations"

    def handle(self, *args, **options):
        expired_drafts = Service.objects.filter(
            status=ServiceStatus.DRAFT,
            last_draft_notification_date__isnull=True,
            creation_date__lte=timezone.now()
            - timedelta(days=settings.DRAFT_AGE_NOTIFICATION_DAYS),
        )
        users = defaultdict(lambda: defaultdict(set))
        for draft in expired_drafts:
            if draft.creator:
                users[draft.creator][draft.structure].add(draft)
            if draft.last_editor:
                users[draft.last_editor][draft.structure].add(draft)

        for user, drafts_by_struct in users.items():
            for structure, drafts in drafts_by_struct.items():
                send_draft_reminder_email(
                    user.email, user.get_short_name(), structure, drafts
                )
                for draft in drafts:
                    draft.last_draft_notification_date = timezone.now()
                    draft.save(update_fields=["last_draft_notification_date"])
