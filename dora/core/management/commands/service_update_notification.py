from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from dora.services.emails import send_services_update_email
from dora.services.models import Service, ServiceStatus, StructureMember


class Command(BaseCommand):
    help = "Notifications pour inciter les contributeurs à mettre à jour leurs services"

    def add_arguments(self, parser):
        parser.add_argument(
            "-n",
            "--dry-run",
            action="store_true",  # https://docs.python.org/3/library/argparse.html#action
            help="N'accomplit aucune action, montre juste le nombre de services & structures concernés ainsi que les destinataires",
        )

    def handle(self, *args, **options):
        # if not settings.IS_TESTING and settings.ENVIRONMENT != "production":
        #    return

        dry_run = options["dry_run"]
        self.stdout.write(
            "Récupération des services publiés et modifiés il y a plus de 6 mois…"
        )

        # Récupération des services dont l'actualisation est conseillée
        services_needed_update = Service.objects.filter(
            status=ServiceStatus.PUBLISHED,
            modification_date__lte=timezone.now() - timedelta(days=180),
        )

        # Map from structure_id to service list
        structure_to_services = dict()

        for service in services_needed_update:
            structure_id = service.structure_id
            if structure_to_services.get(structure_id) is None:
                structure_to_services[structure_id] = [service]
            else:
                structure_to_services[structure_id].append(service)

        self.stdout.write(
            f"{len(structure_to_services)} structures concernés pour un total de {services_needed_update.count()} services"
        )

        mails_count = 0
        user_count = 0
        for structure_id, services in structure_to_services.items():
            mails_count += 1

            # Get structure admin emails
            structure_admins = StructureMember.objects.filter(
                structure_id=structure_id, is_admin=True
            ).all()
            if not structure_admins.exists():
                continue

            emails = [admin.user.email for admin in structure_admins]

            user_count += len(emails)

            if not dry_run:
                send_services_update_email(emails, services)

        self.stdout.write(
            f"{user_count} utilisateurs{' seraient ' if dry_run else ' '}notifiés"
        )
        self.stdout.write(
            f"{mails_count} courriels{' seraient ' if dry_run else ' '}envoyés"
        )
