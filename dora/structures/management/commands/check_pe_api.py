import json

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from dora.sirene.models import Establishment


class Command(BaseCommand):
    help = "Import Pole Emploi agencies in the Structure table, using the Référentiel des agences API"

    def get_pe_credentials(self):
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
            self.stdout.write(
                "Response HTTP Status Code: {status_code}".format(
                    status_code=response.status_code
                )
            )
            return json.loads(response.content)
        except requests.exceptions.RequestException:
            self.stdout.write("HTTP Request failed")

    def get_pe_agencies(self, token):
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
            self.stdout.write(
                "Response HTTP Status Code: {status_code}".format(
                    status_code=response.status_code
                )
            )
            return json.loads(response.content)
        except requests.exceptions.RequestException:
            self.stdout.write("HTTP Request failed")

    def handle(self, *args, **options):

        self.stdout.write(self.style.NOTICE("Authentifying to the PE API"))
        pe_access_token = self.get_pe_credentials()["access_token"]
        self.stdout.write(self.style.NOTICE("Getting list of PE agencies"))
        agencies = self.get_pe_agencies(pe_access_token)

        for agency in agencies:
            # On ignore les 'Relais Pôle Emploi' et les 'Agences spécialisées'
            if agency["type"] in ("RPE", "APES"):
                continue

            name = agency["libelleEtendu"]
            code = agency["code"]
            try:
                siret = agency["siret"]
            except KeyError:
                self.stdout.write(f"SIRET MANQUANT pour {name} ({code})")
                continue
            try:
                establishment = Establishment.objects.get(siret=siret)
            except Establishment.DoesNotExist:
                self.stdout.write(
                    f"SIRET INVALIDE pour {name} ({code}): https://annuaire-entreprises.data.gouv.fr/etablissement/{siret}"
                )
                continue
            communeImplantation = agency["adressePrincipale"]["communeImplantation"]
            if establishment.city_code != communeImplantation:
                self.stdout.write(
                    f"Code INSEE incorrect {name} ({code}): trouvé {communeImplantation}, attendu: {establishment.city_code} — https://annuaire-entreprises.data.gouv.fr/etablissement/{siret}",
                )
