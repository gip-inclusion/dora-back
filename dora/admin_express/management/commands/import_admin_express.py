import os.path
import pathlib
import subprocess
import tempfile

from django.conf import settings
from django.contrib.gis.utils import LayerMapping
from django.core.management.base import BaseCommand

from dora.admin_express.models import City

EXE_7ZR = "/app/.apt/usr/lib/p7zip/7zr" if not settings.DEBUG else "7zr"

# Using the fast OpenDataArchive mirror
# The original is at ftp://Admin_Express_ext:Dahnoh0eigheeFok@ftp3.ign.fr/ADMIN-EXPRESS-COG_3-0__SHP__FRA_WM_2021-05-19.7z
AE_COG_LINK = "http://files.opendatarchives.fr/professionnels.ign.fr/adminexpress/ADMIN-EXPRESS-COG_3-0__SHP__FRA_WM_2021-05-19.7z"
AE_COG_FILE = "ADMIN-EXPRESS-COG_3-0__SHP__FRA_WM_2021-05-19.7z"
USE_TEMP_DIR = not settings.DEBUG


class Command(BaseCommand):
    help = "Import the latest Admin Express COG database"

    def handle(self, *args, **options):
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            if USE_TEMP_DIR:
                the_dir = pathlib.Path(tmp_dir_name)
            else:
                the_dir = pathlib.Path("/tmp")
            self.stdout.write("Saving AE files to " + str(the_dir))

            compressed_AE_file = the_dir / AE_COG_FILE
            print(compressed_AE_file)

            if not os.path.exists(compressed_AE_file):
                self.stdout.write(self.style.NOTICE("Downloading AE COG file"))
                subprocess.run(
                    ["curl", AE_COG_LINK, "-o", compressed_AE_file],
                    check=True,
                )

                self.stdout.write(self.style.NOTICE("Decompression the AE COG"))
                subprocess.run(
                    [EXE_7ZR, "-bd", "x", compressed_AE_file, f"-o{the_dir}"],
                    check=True,
                )

            shapefile = (
                the_dir
                / "ADMIN-EXPRESS-COG_3-0__SHP__FRA_2021-05-19"
                / "ADMIN-EXPRESS-COG"
                / "1_DONNEES_LIVRAISON_2021-05-19"
                / "ADECOG_3-0_SHP_WGS84G_FRA"
                / "COMMUNE.shp"
            )
            # /ADMIN-EXPRESS-COG/1_DONNEES_LIVRAISON_2021-05-19/ADECOG_3-0_SHP_WGS84G_FRA/COMMUNE.shp
            mapping = {
                "code": "INSEE_COM",
                "name": "NOM",
                "department": "INSEE_DEP",
                "region": "INSEE_REG",
                "siren_epci": "SIREN_EPCI",
                "geom": "MULTIPOLYGON",
            }
            self.stdout.write(self.style.SUCCESS("Importing the data"))
            lm = LayerMapping(City, shapefile, mapping)
            lm.save(progress=True, strict=True)
            self.stdout.write(self.style.SUCCESS("Importing successful"))
