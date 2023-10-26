from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone
from mjml import mjml2html

from dora import data_inclusion
from dora.core.emails import send_mail
from dora.services.models import SavedSearch, SavedSearchFrequency
from dora.services.views import _search


def get_saved_search_notifications_to_send():
    # Notifications toutes les deux semaines
    two_weeks_notifications = SavedSearch.objects.filter(
        frequency=SavedSearchFrequency.TWO_WEEKS,
        last_notification_date__lte=timezone.now() - timedelta(days=14),
    )

    # Notifications mensuelles
    monthly_notifications = SavedSearch.objects.filter(
        frequency=SavedSearchFrequency.MONTHLY,
        last_notification_date__lte=timezone.now() - timedelta(days=30),
    )

    return two_weeks_notifications.union(monthly_notifications)


def compute_search_label(saved_search):
    text = f"Services d’insertion à proximité de {saved_search.city_label}"

    if saved_search.category:
        text += f', pour la thématique "{saved_search.category.label}"'

    if saved_search.subcategories.exists():
        labels = saved_search.subcategories.values_list("label", flat=True)
        text += f", pour le(s) besoin(s) : {', '.join(labels)}"

    if saved_search.kinds.exists():
        labels = saved_search.kinds.values_list("label", flat=True)
        text += f", pour le(s) type(s) de service : {', '.join(labels)}"

    if saved_search.fees.exists():
        labels = saved_search.fees.values_list("label", flat=True)
        text += f", avec comme frais à charge : {', '.join(labels)}"

    return text


class Command(BaseCommand):
    help = (
        "Envoi les notifications liées aux recherches sauvegardées par les utilisateurs"
    )

    def handle(self, *args, **options):
        self.stdout.write("Vérification des notifications de recherches sauvegardées")
        saved_searchs = get_saved_search_notifications_to_send()

        di_client = (
            data_inclusion.di_client_factory()
            if not settings.IS_TESTING
            and settings.INCLUDES_DI_SERVICES_IN_SAVED_SEARCH_NOTIFICATIONS
            else None
        )

        num_emails_sent = 0
        for saved_search in saved_searchs:
            category = None
            if saved_search.category:
                category = saved_search.category

            subcategories = None
            if saved_search.subcategories.exists():
                subcategories = saved_search.subcategories.values_list(
                    "value", flat=True
                )

            kinds = None
            if saved_search.kinds.exists():
                kinds = saved_search.kinds.values_list("value", flat=True)

            fees = None
            if saved_search.fees.exists():
                fees = saved_search.fees.values_list("value", flat=True)

            # Récupération des résultats de la recherche
            results = _search(
                None,
                saved_search.city_code,
                [category.value] if category and not subcategories else None,
                subcategories,
                kinds,
                fees,
                di_client,
            )

            # On garde les contenus qui ont été publiés depuis la dernière notification
            updated_services = [
                r
                for r in results
                if datetime.fromisoformat(r["publication_date"]).date()
                > saved_search.last_notification_date
            ]

            if updated_services:
                # Envoi de l'email
                context = {
                    "search_label": compute_search_label(saved_search),
                    "homepage_url": settings.FRONTEND_URL,
                    "updated_services": updated_services[:15],
                    "services_number": len(updated_services),
                }

                num_emails_sent += 1
                send_mail(
                    "Il y a de nouveaux services correspondant à votre alerte",
                    saved_search.user.email,
                    mjml2html(
                        render_to_string("saved-search-notification.mjml", context)
                    ),
                    tags=["saved-search-notification"],
                )

            # Mise à jour de la date de dernière notification
            saved_search.last_notification_date = timezone.now()
            saved_search.save()
        self.stdout.write(f"{num_emails_sent} courriels envoyés")
