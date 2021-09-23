import csv
import json
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from dora.structures.models import Structure, StructureSource, StructureTypology
from dora.users.models import User


def normalize_phone_number(phone):
    return phone.replace(" ", "").replace("-", "")


def get_aurore_to_safir_dict():
    aurore_safir_file_path = (
        Path(__file__).parent.parent.parent
        / "data"
        / "PE-correspondance-aurore-safir-2021-01.csv"
    )
    print(aurore_safir_file_path)

    aurore_to_safir = {}
    with open(aurore_safir_file_path) as aurore_safir_file:
        reader = csv.DictReader(aurore_safir_file, delimiter=";")

        for row in reader:
            aurore_to_safir[row["Aurore"]] = row["Safir"]

    return aurore_to_safir


def get_pe_credentials():
    # https://pole-emploi.io/data/documentation/utilisation-api-pole-emploi/generer-access-token
    try:
        response = requests.post(
            url="https://entreprise.pole-emploi.fr/connexion/oauth2/access_token",
            params={
                "realm": "/partenaire",
            },
            data={
                "grant_type": "client_credentials",
                "client_id": settings.PE_CLIENT_ID,
                "client_secret": settings.PE_CLIENT_SECRET,
                "scope": f"application_{settings.PE_CLIENT_ID} api_referentielagencesv1 organisationpe",
            },
        )
        print(
            "Response HTTP Status Code: {status_code}".format(
                status_code=response.status_code
            )
        )
        return json.loads(response.content)
    except requests.exceptions.RequestException:
        print("HTTP Request failed")


def get_pe_agencies(token):
    # https://pole-emploi.io/data/api/referentiel-agences
    try:
        response = requests.get(
            url="https://api.emploi-store.fr/partenaire/referentielagences/v1/agences",
            params={},
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        print(
            "Response HTTP Status Code: {status_code}".format(
                status_code=response.status_code
            )
        )
        return json.loads(response.content)
    except requests.exceptions.RequestException:
        print("HTTP Request failed")


class Command(BaseCommand):
    help = "Import Pole Emploi agencies in the Structure table, using the Référentiel des agences API"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Parsing Aurore/Safir correspondence"))
        aurore_to_safir = get_aurore_to_safir_dict()

        self.stdout.write(self.style.NOTICE("Authentifying to the PE API"))
        pe_access_token = get_pe_credentials()["access_token"]
        self.stdout.write(self.style.NOTICE("Getting list of PE agencies"))
        agencies = get_pe_agencies(pe_access_token)

        with transaction.atomic(durable=True):
            bot_user = User.objects.get_dora_bot()
            for agency in agencies:
                if agency["type"] == "RPE":
                    # Ignore the 'Relais Pole Emploi'
                    continue
                if agency["type"] == "APES":
                    # Ignore the 'Agence spécialisée'
                    continue

                try:
                    code_safir = aurore_to_safir[agency["code"]]
                except KeyError:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Missing Safir code for {agency["code"]} - {agency["libelleEtendu"]}'
                        )
                    )
                    print(agency)
                    continue
                try:
                    adresse = agency["adressePrincipale"]
                    insee_code = adresse["communeImplantation"]
                    structure, created = Structure.objects.get_or_create(
                        siret=agency["siret"]
                    )
                    if created:
                        structure.source = StructureSource.PE_API
                        structure.creator = bot_user
                    else:
                        self.stdout.write(
                            self.style.NOTICE(
                                f"Structure {structure.name} already exists"
                            )
                        )
                        print(agency)
                    structure.code_safir_pe = code_safir
                    structure.typology = StructureTypology.PE
                    structure.name = agency["libelleEtendu"]
                    structure.phone = normalize_phone_number(
                        agency["contact"].get("telephonePublic", "")
                    )
                    structure.email = agency["contact"].get("email", "")
                    structure.postal_code = adresse["bureauDistributeur"]
                    structure.city_code = insee_code
                    structure.city = adresse["ligne6"][6:]
                    structure.address1 = adresse["ligne4"]
                    structure.address2 = adresse["ligne5"]
                    structure.longitude = adresse["gpsLon"]
                    structure.latitude = adresse["gpsLat"]
                    structure.last_editor = bot_user
                    structure.save()
                except KeyError as err:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Missing field {err} for {agency["code"]} - {agency["libelleEtendu"]}'
                        )
                    )
                    print(agency)
                    continue
                except Exception as err:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Exception for {agency["code"]} - {agency["libelleEtendu"]}'
                        )
                    )
                    print(err)
                    print(agency)
                    continue
