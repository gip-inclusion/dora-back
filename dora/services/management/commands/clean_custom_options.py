from django.core.management.base import BaseCommand

from dora.services.enums import ServiceStatus
from dora.services.models import AccessCondition, ConcernedPublic, Service


class Command(BaseCommand):
    def handle(self, *args, **options):
        # Critères
        access_conditions = AccessCondition.objects.filter(structure__isnull=False)
        self.stdout.write(
            self.style.NOTICE(
                f"Nombre de critères avant nettoyage : {access_conditions.count()}"
            )
        )
        for access_condition in access_conditions:
            if not Service.objects.filter(
                status=ServiceStatus.PUBLISHED, access_conditions=access_condition
            ).exists():
                access_condition.delete()
        self.stdout.write(
            self.style.NOTICE(
                f"Nombre de critères après nettoyage : {access_conditions.all().count()}"
            )
        )

        # Publics
        concerned_publics = ConcernedPublic.objects.filter(structure__isnull=False)
        self.stdout.write(
            self.style.NOTICE(
                f"Nombre de publics avant nettoyage : {concerned_publics.count()}"
            )
        )
        for concerned_public in concerned_publics:
            if not Service.objects.filter(
                status=ServiceStatus.PUBLISHED, concerned_public=concerned_public
            ).exists():
                concerned_public.delete()
        self.stdout.write(
            self.style.NOTICE(
                f"Nombre de publics après nettoyage : {concerned_publics.all().count()}"
            )
        )
