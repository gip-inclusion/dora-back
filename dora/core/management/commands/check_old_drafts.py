from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from dora.core.emails import send_draft_reminder_email
from dora.services.models import Service, ServiceStatus


class Command(BaseCommand):
    help = "Notifications pour les brouillons en souffrance"

    def add_arguments(self, parser):
        parser.add_argument(
            "-n",
            "--dry-run",
            action="store_true",
            help="N'accomplit aucune action, montre juste le nombre de brouillons, d'utilisateurs, et de courriels concernés.",
        )

    def handle(self, *args, **options):
        if settings.ENVIRONMENT != "production":
            return

        dry_run = options["dry_run"]
        self.stdout.write(
            f"Vérification des brouillons de plus de {settings.DRAFT_AGE_NOTIFICATION_DAYS} jours…"
        )
        expired_drafts = Service.objects.filter(
            status=ServiceStatus.DRAFT,
            last_draft_notification_date__isnull=True,
            creation_date__lte=timezone.now()
            - timedelta(days=settings.DRAFT_AGE_NOTIFICATION_DAYS),
        )

        self.stdout.write(f"{expired_drafts.count()} brouillons concernés")
        users = defaultdict(lambda: defaultdict(set))
        for draft in expired_drafts:
            if draft.creator:
                users[draft.creator][draft.structure].add(draft)
            if draft.last_editor:
                users[draft.last_editor][draft.structure].add(draft)

        mails_count = 0
        user_count = 0
        for user, drafts_by_struct in users.items():
            user_count += 1
            for structure, drafts in drafts_by_struct.items():
                mails_count += 1
                if not dry_run:
                    send_draft_reminder_email(
                        user.email, user.get_short_name(), structure, drafts
                    )

                    for draft in drafts:
                        draft.last_draft_notification_date = timezone.now()
                        draft.save(update_fields=["last_draft_notification_date"])
        self.stdout.write(
            f"{user_count} utilisateurs{' seraient ' if dry_run else ' '}notifiés"
        )
        self.stdout.write(
            f"{mails_count} courriels{' seraient ' if dry_run else ' '}envoyés"
        )
