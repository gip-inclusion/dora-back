import csv
import json

import requests
from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand

from dora.admin_express.models import City
from dora.admin_express.utils import arrdt_to_main_insee_code
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

    def print_error(self, writer, agency, establishment, message):
        siret = agency.get("siret")
        addr = agency["adressePrincipale"]
        writer.writerow(
            [
                agency["libelleEtendu"],
                agency["code"],
                message,
                establishment.name if establishment else "",
                f'=HYPERLINK("https://annuaire-entreprises.data.gouv.fr/etablissement/{siret}")'
                if siret
                else "",
                f"{addr['ligne4']} / {addr['ligne5']} / {addr['ligne6']}",
                f"{establishment.address1} / {establishment.postal_code} / {establishment.city}"
                if establishment
                else "",
            ]
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Authentifying to the PE API"))
        pe_access_token = self.get_pe_credentials()["access_token"]
        self.stdout.write(self.style.NOTICE("Getting list of PE agencies"))
        agencies = self.get_pe_agencies(pe_access_token)
        with open("out.csv", "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(
                [
                    "nom agence",
                    "code agence",
                    "erreur",
                    "nom SIRENE",
                    "lien annuaire entreprise",
                    "adresse API",
                    "adresse INSEE",
                ]
            )
            for agency in agencies:
                try:
                    siret = agency["siret"]
                except KeyError:
                    if agency["type"] not in ("RPE", "APES"):
                        self.print_error(writer, agency, None, "SIRET MANQUANT")
                    continue
                try:
                    establishment = Establishment.objects.get(siret=siret)
                except Establishment.DoesNotExist:
                    self.print_error(
                        writer,
                        agency,
                        None,
                        "SIRET INVALIDE",
                    )
                    continue
                # Difficile de comparer les codes postaux, car on a des cedex d'un coté et pas de l'autre
                # postal_code = agency["adressePrincipale"]["bureauDistributeur"]
                # if establishment.postal_code != postal_code:
                #     self.print_error(csvfile,
                #         agency,
                #         f"Code postal incorrect: trouvé {postal_code}, attendu: {establishment.postal_code} — "
                #         f"https://annuaire-entreprises.data.gouv.fr/etablissement/{siret}",
                #     )
                #     print(establishment.name, agency["libelleEtendu"])
                #     continue

                # Les comparaisons de code insee remontent des résultats intéressants, mais aussi de faux positifs,
                # car le code insee de l'Etablishment ne provient a priori pas de la base SIRENE elle même,
                # mais de sa géolocalisation
                commune_implantation = agency["adressePrincipale"][
                    "communeImplantation"
                ]
                if establishment.city_code != commune_implantation:
                    self.print_error(
                        writer,
                        agency,
                        establishment,
                        f"Code INSEE probablement incorrect: trouvé {commune_implantation}, attendu: "
                        f"{establishment.city_code}",
                    )
                    continue

                lat = agency["adressePrincipale"].get("gpsLat")
                lon = agency["adressePrincipale"].get("gpsLon")
                if not lat or not lon:
                    self.print_error(
                        writer,
                        agency,
                        establishment,
                        "Coordonnées géographiques manquantes",
                    )
                    continue

                if commune_implantation[:3] in ["975", "977", "978", "986", "987"]:
                    # Les COM ne sont pas dans Admin Express
                    continue
                city = City.objects.get_from_code(
                    arrdt_to_main_insee_code(commune_implantation)
                )
                if not city:
                    self.print_error(
                        writer,
                        agency,
                        establishment,
                        f"Commune d'implantation inconnue: {commune_implantation}",
                    )
                    continue

                point = Point(float(lon), float(lat), srid=4326)
                if not point.within(city.geom):
                    dist = point.distance(city.geom)
                    if dist > 1:
                        real_city = City.objects.filter(geom__covers=point).first()
                        self.print_error(
                            writer,
                            agency,
                            establishment,
                            f"Les coordonnées géo ne sont pas dans la commune d'implantation ({commune_implantation}) "
                            f"mais à {int(dist)} km ({real_city.name}, {real_city.code})",
                        )
                        continue
