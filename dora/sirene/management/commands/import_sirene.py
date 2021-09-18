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


def get_full_search_text_value(row, parent_name):
    return f"""\
        {row["denominationUsuelleEtablissement"]}
        {row["codePostalEtablissement"]}
        {row["enseigne1Etablissement"]}
        {row["enseigne2Etablissement"]}
        {row["enseigne3Etablissement"]}
        {row["libelleCedexEtablissement"]}
        {row["libelleCommuneEtablissement"]}
        {row["siret"]}
        {parent_name}\
     """


USE_TEMP_DIR = not settings.DEBUG


def commit(rows):
    Establishment.objects.bulk_create(rows)


class Command(BaseCommand):
    help = "Import the latest Sirene database"

    def handle(self, *args, **options):
        with tempfile.TemporaryDirectory() as tmp_dir_name:
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

            establishments_geo_file_url = "https://data.cquest.org/geo_sirene/v2019/last/StockEtablissementActif_utf8_geo.csv.gz"
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

            num_stock_items = 0
            with open(stock_file) as f:
                num_stock_items = sum(1 for line in f)
            with open(stock_file) as units_file:
                legal_units_reader = csv.DictReader(units_file, delimiter=",")
                legal_units = {}
                self.stdout.write(self.style.NOTICE("Parsing legal units"))
                for i, row in enumerate(legal_units_reader):
                    if (i % 1_000_000) == 0:
                        self.stdout.write(
                            self.style.NOTICE(f"{round(100*i/num_stock_items)}% done")
                        )
                    assert row["statutDiffusionUniteLegale"] == "O"
                    legal_units[row["siren"]] = {
                        "denomination": row["denominationUniteLegale"],
                        "diffusable": row["statutDiffusionUniteLegale"],
                        "sigle": row["sigleUniteLegale"],
                        "nom": row["nomUsageUniteLegale"] or row["nomUniteLegale"],
                        "prenom": row["prenomUsuelUniteLegale"]
                        or row["prenom1UniteLegale"],
                        "ess": row["economieSocialeSolidaireUniteLegale"] == "O",
                    }
                num_establishments = 0
                with open(estab_file) as f:
                    num_establishments = sum(1 for line in f)
                with open(estab_file) as establishment_file:
                    reader = csv.DictReader(establishment_file, delimiter=",")
                    self.stdout.write(self.style.NOTICE("Importing establishments"))
                    with transaction.atomic(durable=True):
                        Establishment.objects.all().delete()
                        batch_size = 10_000
                        rows = []
                        for i, row in enumerate(reader):
                            if (i % batch_size) == 0:
                                self.stdout.write(
                                    self.style.NOTICE(
                                        f"{round(100*i/num_establishments)}% done"
                                    )
                                )
                                commit(rows)
                                rows = []
                            try:
                                assert row["statutDiffusionEtablissement"] == "O"
                                code_commune = row["codeCommuneEtablissement"]

                                siren = row["siren"]
                                parent = legal_units.get(siren)
                                parent_name = (
                                    (
                                        parent["denomination"]
                                        or f"{parent['nom']} {parent['prenom']}"
                                    )
                                    if parent
                                    else ""
                                )

                                rows.append(
                                    Establishment(
                                        siren=siren,
                                        siret=row["siret"],
                                        denomination=row[
                                            "denominationUsuelleEtablissement"
                                        ][:100],
                                        ape=row["activitePrincipaleEtablissement"],
                                        code_cedex=row["codeCedexEtablissement"],
                                        code_commune=code_commune,
                                        code_postal=row["codePostalEtablissement"],
                                        complement_adresse=row[
                                            "complementAdresseEtablissement"
                                        ][:38],
                                        distribution_speciale=row[
                                            "distributionSpecialeEtablissement"
                                        ][:26],
                                        enseigne1=row["enseigne1Etablissement"][:50],
                                        enseigne2=row["enseigne2Etablissement"][:50],
                                        enseigne3=row["enseigne3Etablissement"][:50],
                                        is_siege=row["etablissementSiege"] == "true",
                                        is_social=parent["ess"] if parent else False,
                                        repetition_index=row[
                                            "indiceRepetitionEtablissement"
                                        ],
                                        libelle_cedex=row["libelleCedexEtablissement"][
                                            :100
                                        ],
                                        libelle_commune=row[
                                            "libelleCommuneEtablissement"
                                        ][:100],
                                        libelle_voie=row["libelleVoieEtablissement"][
                                            :100
                                        ],
                                        nic=row["nic"],
                                        numero_voie=row["numeroVoieEtablissement"],
                                        diffusable=row["statutDiffusionEtablissement"]
                                        == "O",
                                        type_voie=row["typeVoieEtablissement"],
                                        denomination_parent=parent_name,
                                        sigle_parent=parent["sigle"][:20]
                                        if parent
                                        else "",
                                        full_search_text=get_full_search_text_value(
                                            row, parent_name
                                        ),
                                        longitude=row["longitude"]
                                        if row["longitude"]
                                        else None,
                                        latitude=row["latitude"]
                                        if row["latitude"]
                                        else None,
                                    )
                                )

                            except DataError as err:
                                self.stdout.write(self.style.ERROR(err))
                                self.stdout.write(self.style.ERROR(row))
                        commit(rows)

                self.stdout.write(self.style.SUCCESS("Import successful"))
