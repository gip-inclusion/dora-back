from collections import defaultdict
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from dora.core.emails import send_draft_reminder_email
from dora.services.models import Service, ServiceStatus


class Command(BaseCommand):
    help = "Mass-send user invitations"

    def handle(self, *args, **options):
        expired_drafts = Service.objects.filter(
            status=ServiceStatus.DRAFT,
            creation_date__lte=timezone.now() - timedelta(days=7),
        )
        users = defaultdict(lambda: defaultdict(set))
        for draft in expired_drafts:
            users[draft.creator][draft.structure].add(draft)
            users[draft.last_editor][draft.structure].add(draft)

        for user, drafts_by_struct in users.items():
            for structure, drafts in drafts_by_struct.items():
                print(user, structure, drafts)
                send_draft_reminder_email(
                    user.email, user.get_short_name(), structure, drafts
                )
