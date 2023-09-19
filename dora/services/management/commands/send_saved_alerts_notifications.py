from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from dora.services.models import SavedSearch, SavedSearchFrequency


def get_alerts_to_send():
    # Alerte tous les deux semaines
    two_weeks_alerts = SavedSearch.objects.filter(
        frequency=SavedSearchFrequency.objects.filter(value="two-weeks").first(),
        last_notification_date__lte=timezone.now() - timedelta(days=14),
    )

    # Alertes mensuels
    monthly_alerts = SavedSearch.objects.filter(
        frequency=SavedSearchFrequency.objects.filter(value="monthly").first(),
        last_notification_date__lte=timezone.now() - timedelta(days=30),
    )

    return two_weeks_alerts.union(monthly_alerts)


class Command(BaseCommand):
    help = "Envoi les alertes liés aux recherches sauvegardées par les utilisateurs"

    def handle(self, *args, **options):
        alerts = get_alerts_to_send()

        for alert in alerts:
            # Récupération des résultats de la recherche

            # On garde les contenus qui ont été publiés depuis la dernière notification

            # Envoi de l'email

            # Mise à jour de la date de dernière notification
            alert.last_notification_date = timezone.now()
            alert.save()
