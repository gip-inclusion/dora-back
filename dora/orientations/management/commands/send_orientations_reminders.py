from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from dora.orientations.emails import send_orientation_reminder_emails
from dora.orientations.models import Orientation, OrientationStatus


class Command(BaseCommand):
    help = "Notifications pour les orientations en souffrance"

    def add_arguments(self, parser):
        parser.add_argument(
            "-n",
            "--dry-run",
            action="store_true",
            help="N'accomplit aucune action, montre juste le nombre d’orientations concernées.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.NOTICE("DRY RUN"))
        else:
            self.stdout.write(self.style.WARNING("PRODUCTION RUN"))

        self.stdout.write(
            f"Vérification des orientations de plus de {settings.NUM_DAYS_BEFORE_ORIENTATIONS_NOTIFICATION} jours…"
        )
        cutoff_date = timezone.now() - timedelta(
            days=settings.NUM_DAYS_BEFORE_ORIENTATIONS_NOTIFICATION
        )
        orientations = Orientation.objects.filter(
            status=OrientationStatus.PENDING
        ).filter(
            Q(last_reminder_email_sent__isnull=True, creation_date__lte=cutoff_date)
            | Q(last_reminder_email_sent__lte=cutoff_date)
        )

        self.stdout.write(f"{orientations.count()} orientations concernées")
        for orientation in orientations:
            if not dry_run:
                send_orientation_reminder_emails(orientation)
                orientation.last_reminder_email_sent = timezone.now()
                orientation.save()
