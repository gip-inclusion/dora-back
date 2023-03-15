import csv
import tempfile

from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand

from dora.admin_express.models import City
from dora.admin_express.utils import arrdt_to_main_insee_code
from dora.services.models import Service


class Command(BaseCommand):
    def display_error(self, category, service, message):
        self.csv_writer.writerow(
            [category, service.get_frontend_url(), service.get_admin_url(), message]
        )

    def send_mail(self, file):
        if not settings.ADMINS:
            return

        email = EmailMessage(
            "[DORA] Rapport d'analyse de qualité des services",
            "Voir document joint",
            settings.SERVER_EMAIL,
            [a[1] for a in settings.ADMINS],
        )
        email.attach_file(file.name)
        email.send(fail_silently=False)

    def handle(self, *args, **options):
        with tempfile.NamedTemporaryFile(
            suffix=".csv", mode="w", newline=""
        ) as tmp_file:
            self.csv_writer = csv.writer(tmp_file, delimiter=",")
            self.csv_writer.writerow(
                ["Catégorie", "Lien front", "Lien back", "Message"]
            )
            published_services = Service.objects.published()
            for s in published_services.filter(location_kinds__value="a-distance"):
                self.check_remote(s)
            for s in published_services.filter(location_kinds__value="en-presentiel"):
                self.check_geo(s)
            for s in published_services:
                self.check_typology(s)
                self.check_modalities(s)

            tmp_file.seek(0)
            self.send_mail(tmp_file)

    def check_geo(self, s):
        if s.geom is None:
            self.display_error("geo", s, "Pas de géolocalisation")

        elif not s.address1 or not s.postal_code or not s.city_code or not s.city:
            self.display_error(
                "geo",
                s,
                f"Adresse incomplete (address1: {s.address1}; postal_code: {s.postal_code}; city_code: {s.city_code}; city: {s.city}",
            )

        elif s.postal_code[0:2] != s.city_code[0:2].replace("2A", "20").replace(
            "2B", "20"
        ):
            self.display_error(
                "geo",
                s,
                f"Code postal et code insee non cohérents: postal_code: {s.postal_code}; city_code: {s.city_code}",
            )
        else:
            city = City.objects.get_from_code(arrdt_to_main_insee_code(s.city_code))
            if not city:
                self.display_error(
                    "geo", s, f"code insee incorrect: city_code: {s.city_code}"
                )

            elif not city.geom.contains(s.geom):
                s = (
                    Service.objects.filter(pk=s.pk)
                    .annotate(distance=Distance("geom", city.geom))
                    .first()
                )
                if s.distance.km > 1:
                    self.display_error(
                        "geo",
                        s,
                        f"géolocalisation hors de la commune ({int(s.distance.km)} km)",
                    )

    def check_remote(self, s):
        if not s.remote_url:
            self.display_error(
                "remote",
                s,
                "Pas d'URL pour un service à distance",
            )

    def check_typology(self, s):
        if not s.kinds.all().exists():
            self.display_error(
                "typology",
                s,
                "Pas de type",
            )
        if not s.categories.all().exists():
            self.display_error(
                "typology",
                s,
                "Pas de categorie",
            )
        if (
            not s.subcategories.all().exists()
            and s.categories.exclude(value="acc-global-indiv").exists()
        ):
            cats = "; ".join(s.categories.all().values_list("value", flat=True))
            self.display_error(
                "typology",
                s,
                f"Pas de besoin; catégories {cats}",
            )

    def check_modalities(self, s):
        if s.beneficiaries_access_modes.filter(value="envoyer-courriel").exists() and (
            not s.contact_email or not s.is_contact_info_public
        ):
            self.display_error(
                "modalities",
                s,
                "demande l'envoi d'un courriel, mais pas d'email visible",
            )
        if s.beneficiaries_access_modes.filter(value="telephoner").exists() and (
            not s.contact_phone or not s.is_contact_info_public
        ):
            self.display_error(
                "modalities",
                s,
                "demande un appel téléphonique, mais pas de numéro visible",
            )
        if (
            s.beneficiaries_access_modes.filter(value="se-presenter").exists()
            and not s.address1
            and not s.city
        ):
            self.display_error(
                "modalities",
                s,
                "demande à se présenter, mais pas d'adresse renseignée visible",
            )
        if (
            s.coach_orientation_modes.filter(value="envoyer-courriel").exists()
            and not s.contact_email
        ):
            self.display_error(
                "modalities",
                s,
                "demande l'envoi d'un courriel, mais pas d'email",
            )
        if (
            s.coach_orientation_modes.filter(value="telephoner").exists()
            and not s.contact_phone
        ):
            self.display_error(
                "modalities",
                s,
                "demande un appel téléphonique, mais pas de numéro",
            )
        if s.coach_orientation_modes.filter(
            value="envoyer-fiche-prescription"
        ).exists() and not (s.forms or s.online_form):
            self.display_error(
                "modalities",
                s,
                "demande l'envoi d'un formulaire, mais pas de formulaire renseigné",
            )
        if s.coach_orientation_modes.filter(
            value="envoyer-formulaire"
        ).exists() and not (s.forms or s.online_form):
            self.display_error(
                "modalities",
                s,
                "demande l'envoi d'un formulaire, mais pas de formulaire renseigné",
            )
