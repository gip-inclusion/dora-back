import csv
import os.path
import pathlib
import subprocess
import tempfile

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.utils import DataError

from dora.sirene.models import Establishment

# Documentation des variables SIRENE : https://www.sirene.fr/static-resources/htm/v_sommaire.htm


def clean_spaces(string):
    return string.replace("  ", " ").strip()


USE_TEMP_DIR = not settings.DEBUG


def commit(rows):
    Establishment.objects.bulk_create(rows)


class Command(BaseCommand):
    help = "Import the latest Sirene database"

    def download_data(self, tmp_dir_name):
        if USE_TEMP_DIR:
            the_dir = pathlib.Path(tmp_dir_name)
        else:
            the_dir = pathlib.Path("/tmp")
        self.stdout.write("Saving SIRENE files to " + str(the_dir))

        legal_units_file_url = (
            "https://files.data.gouv.fr/insee-sirene/StockUniteLegale_utf8.zip"
        )
        zipped_stock_file = the_dir / "StockUniteLegale_utf8.zip"

        if not os.path.exists(zipped_stock_file):
            self.stdout.write(self.style.NOTICE("Downloading legal units file"))
            subprocess.run(
                ["curl", legal_units_file_url, "-o", zipped_stock_file],
                check=True,
            )

            self.stdout.write(self.style.NOTICE("Unzipping legal units file"))
            subprocess.run(
                ["unzip", zipped_stock_file, "-d", the_dir],
                check=True,
            )

        stock_file = the_dir / "StockUniteLegale_utf8.csv"

        establishments_geo_file_url = "https://files.data.gouv.fr/geo-sirene/last/StockEtablissementActif_utf8_geo.csv.gz"
        gzipped_estab_file = the_dir / "StockEtablissementActif_utf8_geo.csv.gz"

        if not os.path.exists(gzipped_estab_file):
            self.stdout.write(self.style.NOTICE("Downloading establishments file"))
            subprocess.run(
                ["curl", establishments_geo_file_url, "-o", gzipped_estab_file],
                check=True,
            )

            self.stdout.write(self.style.NOTICE("Unzipping establishments file"))
            subprocess.run(
                ["gzip", "-dk", gzipped_estab_file],
                check=True,
            )

        estab_file = the_dir / "StockEtablissementActif_utf8_geo.csv"

        return stock_file, estab_file

    def get_ul_name(self, row):
        if row["categorieJuridiqueUniteLegale"] == "1000":
            # personne physique
            unit_name = row["denominationUsuelle1UniteLegale"] or (
                f'{row["prenomUsuelUniteLegale"]} {row["nomUsageUniteLegale"] or row["nomUniteLegale"]}'
            )
        else:
            # personne morale
            unit_name = (
                row["denominationUsuelle1UniteLegale"] or row["denominationUniteLegale"]
            )

            if row["sigleUniteLegale"]:
                unit_name += f' — {row["sigleUniteLegale"]}'

        return unit_name

    def get_name(self, row):
        denom = row["denominationUsuelleEtablissement"]
        enseigne1 = (
            row["enseigne1Etablissement"]
            if row["enseigne1Etablissement"] != denom
            else ""
        )
        return clean_spaces(f"{denom} {enseigne1}")

    def get_address1(self, row):
        return clean_spaces(
            f'{row["numeroVoieEtablissement"]} {row["indiceRepetitionEtablissement"]} {row["typeVoieEtablissement"]} {row["libelleVoieEtablissement"]}'
        )

    def get_city_name(self, row):
        return clean_spaces(
            f'{row["libelleCedexEtablissement"] or row["libelleCommuneEtablissement"]} {row["distributionSpecialeEtablissement"]}'
        )

    def create_establishment(self, siren, parent_name, row):
        name = self.get_name(row)[:255]
        parent_name = parent_name[:255]
        full_search_text = f"{name} {parent_name}" if name != parent_name else name
        return Establishment(
            siren=siren[:9],
            siret=row["siret"][:14],
            name=name,
            parent_name=parent_name,
            address1=self.get_address1(row)[:255],
            address2=row["complementAdresseEtablissement"][:255],
            city=self.get_city_name(row)[:255],
            city_code=row["codeCommuneEtablissement"][:5],
            postal_code=(
                row["codeCedexEtablissement"] or row["codePostalEtablissement"]
            )[:5],
            ape=row["activitePrincipaleEtablissement"][:6],
            is_siege=row["etablissementSiege"] == "true",
            longitude=row["longitude"] if row["longitude"] else None,
            latitude=row["latitude"] if row["latitude"] else None,
            full_search_text=full_search_text,
        )

    def handle(self, *args, **options):
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            stock_file, estab_file = self.download_data(tmp_dir_name)

            num_stock_items = 0
            with open(stock_file) as f:
                num_stock_items = sum(1 for line in f)

            legal_units = {}
            with open(stock_file) as units_file:
                legal_units_reader = csv.DictReader(units_file, delimiter=",")

                self.stdout.write(self.style.NOTICE("Parsing legal units"))

                for i, row in enumerate(legal_units_reader):
                    if (i % 1_000_000) == 0:
                        self.stdout.write(
                            self.style.NOTICE(f"{round(100*i/num_stock_items)}% done")
                        )
                    if row["etatAdministratifUniteLegale"] == "A":
                        # On ignore les unités légales fermées
                        legal_units[row["siren"]] = self.get_ul_name(row)

                self.stdout.write(self.style.NOTICE("Counting establishments"))

                num_establishments = 0
                with open(estab_file) as f:
                    num_establishments = sum(1 for line in f)
                last_prog = 0

            with open(estab_file) as establishment_file:
                self.stdout.write(self.style.NOTICE("Importing establishments"))
                reader = csv.DictReader(establishment_file, delimiter=",")

                with transaction.atomic(durable=True):
                    self.stdout.write(self.style.WARNING("Emptying current table"))
                    Establishment.objects.all().delete()
                    batch_size = 1_000
                    rows = []
                    for i, row in enumerate(reader):
                        if (i % batch_size) == 0:
                            prog = round(100 * i / num_establishments)
                            if prog != last_prog:
                                last_prog = prog
                            self.stdout.write(self.style.NOTICE(f"{prog}% done"))
                            commit(rows)
                            rows = []
                        try:
                            siren = row["siren"]
                            parent = legal_units.get(siren)
                            if parent:
                                rows.append(
                                    self.create_establishment(
                                        siren,
                                        parent,
                                        row,
                                    )
                                )

                        except DataError as err:
                            self.stdout.write(self.style.ERROR(err))
                            self.stdout.write(self.style.ERROR(row))

                    commit(rows)

                self.stdout.write(self.style.SUCCESS("Import successful"))
