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
from dora.structures.models import Structure, StructureSource, StructureTypology
from dora.users.models import User

# SORTED_SOURCES = ["mes-aides"]
SORTED_SOURCES = ["itou"]  # , "siao", "cd72", "cd35"]

BASE_URL = furl(settings.DATA_INCLUSION_URL)


def get_results_page(url, page_number):
    paginated_url = url.copy().add({"page": page_number})
    print(paginated_url)
    response = requests.get(
        paginated_url,
        params={},
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {settings.DATA_INCLUSION_API_KEY}",
        },
    )
    print(
        "Response HTTP Status Code: {status_code}".format(
            status_code=response.status_code
        )
    )
    return json.loads(response.content)["items"]


def get_structures(source):
    structures = []
    page = 1

    url = BASE_URL.add(
        path="structures/",
        args={"source": source, "size": 100, "departement": "08"},
    )

    while True:
        page_structures = get_results_page(url, page)
        if len(page_structures):
            structures += page_structures
        else:
            break
        page += 1
    return structures


class Command(BaseCommand):
    # TODO
    help = ""

    def handle(self, *args, **options):
        for source in SORTED_SOURCES:

            self.stdout.write(f"Importing: {source}")
            try:
                structures = get_structures(source)
            except requests.exceptions.RequestException:
                print("HTTP Request failed")
                break
            # import pprint
            #
            # pprint.pprint(structures)
            self.import_structures(source, structures)

    def import_structures(self, source, structures):
        # for structure in structures:
        #     try:
        #         s = Structure.objects.get(siret=structure["siret"])
        #         self.stdout.write(f"Deleting: {s.name}")
        #         s.delete()
        #     except Structure.DoesNotExist:
        #         pass

        bot_user = User.objects.get_dora_bot()

        existing_structures_sirets = set(
            Structure.objects.all().values_list("siret", flat=True)
        )
        structures_to_import = [
            s for s in structures if s["siret"] not in existing_structures_sirets
        ]

        for di_structure in structures_to_import:
            if di_structure["structure_parente"]:
                print(di_structure)
            continue
            self.stdout.write(f"Importing: {di_structure['nom']}")
            return
            try:
                establishment = Establishment.objects.get(siret=di_structure["siret"])
            except Establishment.DoesNotExist:
                self.stdout.write(f"Siret incorrect: {di_structure['siret']}")
                continue

            typology, _created = StructureTypology.objects.get_or_create(
                value=di_structure["typologie"]
            )
            source, _created = StructureSource.objects.get_or_create(
                value=f"di-{source}",
                defaults={"label": f"Data Inclusion ({source})"},
            )
            structure = Structure.objects.create(
                siret=di_structure["siret"],
                name=di_structure["nom"] or establishment.name,
                address1=di_structure["adresse"] or establishment.address1,
                address2=di_structure["complement_adresse"] or "",
                city_code=di_structure["code_insee"] or establishment.city_code,
                postal_code=di_structure["code_postal"] or establishment.postal_code,
                city=di_structure["commune"] or establishment.city,
                latitude=di_structure["latitude"] or establishment.latitude,
                longitude=di_structure["longitude"] or establishment.longitude,
                email=di_structure["courriel"] or "",
                phone=utils.normalize_phone_number(di_structure["telephone"] or ""),
                url=di_structure["site_web"] or "",
                full_desc=di_structure["presentation_detail"] or "",
                short_desc=di_structure["presentation_resume"] or "",
                typology=typology,
                opening_hours=di_structure["horaires_ouverture"],
                other_labels=di_structure["labels_autres"],
                accesslibre_url=di_structure["accessibilite"],
                # parent=di_structure['structure_parente'],
                ape=establishment.ape,
                source=source,
                creator=bot_user,
                last_editor=bot_user,
                modification_date=timezone.now(),
            )

            structure.national_labels.set(di_structure["labels_nationaux"])

            send_moderation_notification(
                structure,
                bot_user,
                f"Structure importée de Data Inclusion ({source})",
                ModerationStatus.VALIDATED,
            )
