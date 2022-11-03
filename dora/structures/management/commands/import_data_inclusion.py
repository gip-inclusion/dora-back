import json

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from furl import furl

from dora.core import utils
from dora.core.models import ModerationStatus
from dora.core.notify import send_moderation_notification
from dora.sirene.models import Establishment
from dora.structures.models import (
    Structure,
    StructureNationalLabel,
    StructureSource,
    StructureTypology,
)
from dora.users.models import User

# Documentation DI : https://data-inclusion-api-prod.osc-secnum-fr1.scalingo.io/api/v0/docs

BASE_URL = furl(settings.DATA_INCLUSION_URL)


class Command(BaseCommand):
    help = "Importe les nouvelles structures Inclusion Connect qui n'existent pas encore dans Dora"

    def add_arguments(self, parser):
        parser.add_argument("source", type=str)
        parser.add_argument("--department", type=str)

    def handle(self, *args, **options):
        department = options["department"]
        source = options["source"]

        self.stdout.write(self.style.SUCCESS(f"Import de la source: {source}"))
        try:
            structures = self.get_structures(source, department)
            self.import_structures(source, structures)
        except requests.exceptions.RequestException as e:
            self.stderr.write(self.style.ERROR(e))

    def get_structures(self, source, department):
        structures = []
        args = {"source": source, "size": 100}
        if department:
            args["departement"] = department

        url = BASE_URL.add(
            path="structures/",
            args=args,
        )

        for results in self.get_pages(url):
            structures += results

        return structures

    def get_pages(self, url):
        page = 1
        while True:
            paginated_url = url.copy().add({"page": page})
            self.stdout.write(f"Chargement de {paginated_url}")
            response = requests.get(
                paginated_url,
                params={},
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": f"Bearer {settings.DATA_INCLUSION_API_KEY}",
                },
            )
            if response.status_code != 200:
                self.stderr.write(
                    self.style.ERROR(
                        f"Erreur dans la récupération des données\n{url}: {response.status_code}"
                    )
                )
                return

            result = json.loads(response.content)["items"]
            if len(result):
                yield result
                page += 1
            else:
                return

    def import_structures(self, source_value, structures):
        bot_user = User.objects.get_dora_bot()
        source, _created = StructureSource.objects.get_or_create(
            value=f"di-{source_value}",
            defaults={"label": source_value},
        )
        if _created:
            self.stdout.write(
                self.style.ERROR(
                    f"Source: di-{source_value} inexistante. Pensez à renseigner son label dans l'interface "
                    f"d'administration"
                )
            )
        num_imported = 0
        for s in structures:
            if Structure.objects.filter(siret=s["siret"]).exists():
                # Les doublons sont attendus -- itou a une unicité sur le couple (siret, typologie) par exemple
                # alors que Dora a pour l'instant une unicité stricte sur le siret (hors antennes).
                continue
            if s["structure_parente"]:
                # Les antennes ne sont pas gérées pour l'instant
                continue
            try:
                establishment = Establishment.objects.get(siret=s["siret"])
            except Establishment.DoesNotExist:
                self.stdout.write(
                    self.style.NOTICE(
                        f"Siret incorrect, ignoré : {s['siret']} ({s['nom']})"
                    )
                )
                continue
            try:
                typology = None
                if s["typologie"]:
                    typology, _created = StructureTypology.objects.get_or_create(
                        value=s["typologie"]
                    )
                if _created:
                    self.stdout.write(
                        self.style.ERROR(
                            f"typology: {s['typologie']} inexistante. Pensez à renseigner son label dans l'interface "
                            f"d'administration"
                        )
                    )
                structure = Structure.objects.create(
                    data_inclusion_id=s["id"],
                    siret=s["siret"],
                    name=s["nom"] or establishment.name,
                    address1=s["adresse"] or establishment.address1,
                    address2=s["complement_adresse"] or "",
                    city_code=s["code_insee"] or establishment.city_code,
                    postal_code=s["code_postal"] or establishment.postal_code,
                    city=s["commune"] or establishment.city,
                    latitude=s["latitude"] or establishment.latitude,
                    longitude=s["longitude"] or establishment.longitude,
                    email=s["courriel"] or "",
                    phone=utils.normalize_phone_number(s["telephone"] or ""),
                    url=s["site_web"] or "",
                    full_desc=s["presentation_detail"] or "",
                    short_desc=s["presentation_resume"] or "",
                    typology=typology,
                    accesslibre_url=s["accessibilite"],
                    ape=establishment.ape,
                    source=source,
                    creator=bot_user,
                    last_editor=bot_user,
                    modification_date=timezone.now(),
                    # Champs non gérés pour l'instant
                    # opening_hours=s["horaires_ouverture"],
                    # other_labels=",".join(s["labels_autres"]),
                    # parent=s['structure_parente'],
                )
                for label in s["labels_nationaux"]:
                    new_label, _created = StructureNationalLabel.objects.get_or_create(
                        value=label
                    )
                    if _created:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Label national: {label} inexistant. Pensez à le compléter dans l'interface "
                                f"d'administration"
                            )
                        )
                    structure.national_labels.add(new_label)

                send_moderation_notification(
                    structure,
                    bot_user,
                    f"Structure importée de Data Inclusion ({source})",
                    ModerationStatus.VALIDATED,
                )
                num_imported += 1

            except Exception as e:
                print(s)
                self.stderr.write(s)
                self.stderr.write(self.style.ERROR(e))
        self.stdout.write(self.style.SUCCESS(f"{num_imported} structures importées"))
