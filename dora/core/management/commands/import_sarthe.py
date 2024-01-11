import csv
import json
import re
import time

import requests
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.utils import dateparse, timezone
from django.utils.text import Truncator
from furl import furl

from dora.core import utils
from dora.core.constants import SIREN_POLE_EMPLOI
from dora.core.models import ModerationStatus
from dora.core.notify import send_moderation_notification
from dora.core.utils import normalize_description
from dora.services.enums import ServiceStatus
from dora.services.models import (
    AccessCondition,
    BeneficiaryAccessMode,
    ConcernedPublic,
    LocationKind,
    Requirement,
    Service,
    ServiceCategory,
    ServiceFee,
    ServiceSource,
    ServiceSubCategory,
)
from dora.sirene.models import Establishment
from dora.structures.models import (
    Structure,
    StructureSource,
    StructureTypology,
)
from dora.users.models import User

BOT_USER = User.objects.get_dora_bot()
STRUCTURES_SOURCE, _ = StructureSource.objects.get_or_create(
    value="cd72",
    defaults={"label": "Conseil départemental de la Sarthe (import DORA)"},
)
SERVICES_SOURCES, _ = ServiceSource.objects.get_or_create(
    value="cd72",
    defaults={"label": "Conseil départemental de la Sarthe (import DORA)"},
)
FEE_FREE = ServiceFee.objects.get(value="gratuit")
FEE_NONFREE = ServiceFee.objects.get(value="payant")
ONSITE_LOCATION = LocationKind.objects.get(value="en-presentiel")


def clean_field(value, max_length, default_value):
    if not value:
        return default_value
    return Truncator(value).chars(max_length)


def cust_choice_to_objects(Model, values):
    if values:
        return Model.objects.filter(
            name__in=[v.strip() for v in values], structure=None
        )
    return []


def get_geoloc(address, postal_code):
    time.sleep(0.1)  # Pour interroger l'api adresse à un rythme raisonnable
    url = furl("https://api-adresse.data.gouv.fr").add(
        path="/search/",
        args={
            "q": address,
            "postcode": postal_code,
            "autocomplete": 0,
            "limit": 1,
        },
    )
    response = requests.get(
        url,
        params={},
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    if response.status_code != 200:
        print(address, postal_code)
        raise Exception(f"Erreur dans la récupération des données: {response.content}")

    result = json.loads(response.content)
    if result["features"]:
        feat = result["features"][0]
        if feat["properties"]["score"] > 0.5:
            return feat
        else:
            return


class Command(BaseCommand):
    help = "Importe les nouvelles structures Data Inclusion qui n'existent pas encore dans Dora"

    def add_arguments(self, parser):
        parser.add_argument("structures_file")
        parser.add_argument("services_file")

    def handle(self, *args, **options):
        structures_file = options["structures_file"]
        services_file = options["services_file"]
        try:
            id_to_struct = self.import_structures(structures_file)
            self.import_services(services_file, id_to_struct)
        except requests.exceptions.RequestException as e:
            self.stderr.write(self.style.ERROR(e))

    def import_structures(self, filename):
        num_imported = 0
        id_to_struct = {}
        with open(filename) as structures_file:
            reader = csv.DictReader(structures_file, delimiter=",")

            for i, row in enumerate(reader):
                structure, created = self.get_or_create_structure(row)
                if structure:
                    if created:
                        num_imported += 1
                    id_to_struct[row["id"]] = structure

        self.stdout.write(self.style.SUCCESS(f"{num_imported} structures importées"))
        return id_to_struct

    def get_or_create_structure(self, row):
        existing_structure = Structure.objects.filter(id=row["id"]).first()
        if existing_structure:
            return existing_structure, False
        if not row.get("siret") and not row.get("siret_parent"):
            return None, False
        if row.get("siret"):
            try:
                return Structure.objects.get(siret=row["siret"]), False
            except Structure.DoesNotExist:
                try:
                    establishment = Establishment.objects.get(siret=row["siret"])
                except Establishment.DoesNotExist:
                    return None, False
                structure = Structure.objects.create_from_establishment(
                    establishment, structure_id=row["id"]
                )
                self.fill_structure(structure, row)
                structure.save()
                return structure, True
        else:
            parent = Structure.objects.get(siret=row["siret_parent"])
            structure = Structure.objects.create(parent=parent, id=row["id"])
            self.fill_structure(structure, row)
            structure.save()
            return structure, True

    def fill_structure(self, structure, row):
        structure.name = row["nom"]
        structure.short_desc, structure.full_desc = normalize_description(
            row["presentation_detail"], 280
        )
        structure.phone = utils.normalize_phone_number(row["telephone"] or "")
        structure.email = clean_field(row["courriel"], 254, "")
        structure.url = clean_field(row["site_web"], 200, "")
        structure.opening_hours_details = row["horaires_ouverture"]

        if row["typologie"]:
            typology = StructureTypology.objects.get(value=row["typologie"])
            structure.typology = typology
        if row["adresse"] and row["code_postal"]:
            feat = get_geoloc(row["adresse"], row["code_postal"])
            if feat:
                structure.address1 = feat["properties"]["name"]
                structure.postal_code = feat["properties"]["postcode"]
                structure.city = feat["properties"]["city"]
                structure.city_code = feat["properties"]["citycode"]
                structure.longitude = feat["geometry"]["coordinates"][0]
                structure.latitude = feat["geometry"]["coordinates"][1]
                structure.geocoding_score = feat["properties"]["score"]

        structure.creator = BOT_USER
        structure.last_editor = BOT_USER
        structure.source = STRUCTURES_SOURCE

        send_moderation_notification(
            structure,
            BOT_USER,
            "Structure importée en masse depuis le CD 72",
            ModerationStatus.VALIDATED,
        )

    def import_services(self, filename, id_to_struct):
        num_imported = 0
        with open(filename) as services_file:
            reader = csv.DictReader(services_file, delimiter=",")

            for i, row in enumerate(reader):
                structure = id_to_struct.get(row["structure_id"])
                if not structure:
                    continue

                if self.create_service(structure, row):
                    num_imported += 1

        self.stdout.write(self.style.SUCCESS(f"{num_imported} services importés"))

    def create_service(self, structure, row):
        if structure.siret and structure.siret.startswith(SIREN_POLE_EMPLOI):
            return False
        if Service.objects.filter(id=row["id"]).exists():
            return False

        tel = row["telephone"].split("\n")[0]
        service = Service.objects.create(
            id=row["id"],
            structure=structure,
            name=row["nom"],
            short_desc=clean_field(row["presentation_resume"], 280, ""),
            full_desc=f"{row['presentation_detail']}\n{row['presentation_detail_2']}",
            fee_condition=FEE_NONFREE if row["frais"] == "true" else FEE_FREE,
            fee_details=row["frais_autres"],
            recurrence=clean_field(row["recurrence"], 140, ""),
            suspension_date=timezone.make_aware(
                dateparse.parse_datetime(row["date_suspension"])
            )
            if row["date_suspension"]
            else None,
            contact_name=row["contact_nom_prenom"].split("\n")[0] or "",
            contact_phone=utils.normalize_phone_number(tel or ""),
            contact_email=row["courriel"].split("\n")[0] or "",
            modification_date=timezone.make_aware(
                dateparse.parse_datetime(row["date_maj"])
            )
            if row["date_maj"]
            else timezone.now(),
            diffusion_zone_type="department",
            diffusion_zone_details=72,
            source=SERVICES_SOURCES,
            creator=BOT_USER,
            last_editor=BOT_USER,
        )

        has_address = False
        if row["adresse"] and row["code_postal"]:
            feat = get_geoloc(row["adresse"], row["code_postal"])
            if feat:
                service.address1 = feat["properties"]["name"]
                service.postal_code = feat["properties"]["postcode"]
                service.city = feat["properties"]["city"]
                service.city_code = feat["properties"]["citycode"]
                service.geocoding_score = feat["properties"]["score"]
                lon = feat["geometry"]["coordinates"][0]
                lat = feat["geometry"]["coordinates"][1]
                service.geom = Point(lon, lat, srid=4326)
                has_address = True
        if not has_address:
            service.address1 = structure.address1
            service.postal_code = structure.postal_code
            service.city = structure.city
            service.city_code = structure.city_code
            service.geocoding_score = structure.geocoding_score
            service.geom = Point(structure.longitude, structure.latitude, srid=4326)

        service.beneficiaries_access_modes.add(
            BeneficiaryAccessMode.objects.get(value="autre")
        )
        service.beneficiaries_access_modes_other = row[
            "modes_orientation_beneficiaire_autres"
        ][:280]
        service.status = ServiceStatus.PUBLISHED
        service.publication_date = timezone.now()

        concerned_publics = cust_choice_to_objects(
            ConcernedPublic, self._str_to_list(row["profils_bruts"])
        )
        if concerned_publics:
            service.concerned_public.set(concerned_publics)

        access_conditions = cust_choice_to_objects(
            AccessCondition, self._str_to_list(row["conditions_acces"])
        )
        if access_conditions:
            service.access_conditions.set(access_conditions)

        requirements = cust_choice_to_objects(
            Requirement, self._str_to_list(row["pre_requis"])
        )
        if requirements:
            service.requirements.set(requirements)

        subcats = self._str_to_list(row["thematiques"])
        cats = [s.split("--")[0] for s in subcats]
        service.categories.set(self._values_to_objects(ServiceCategory, cats))
        service.subcategories.set(self._values_to_objects(ServiceSubCategory, subcats))

        service.location_kinds.add(ONSITE_LOCATION)
        service.save()
        send_moderation_notification(
            service,
            BOT_USER,
            "Service importé en masse depuis le CD 72",
            ModerationStatus.VALIDATED,
        )
        return True

    def _values_to_objects(self, Model, values):
        if values:
            return Model.objects.filter(value__in=values)
        return []

    def _str_to_list(self, string):
        if string:
            split_lst = re.split(r"[,\n]", string)
            return [item.strip() for item in split_lst]
        return []
