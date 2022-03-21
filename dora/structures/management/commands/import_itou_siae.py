import csv
import logging
from itertools import groupby
from pathlib import Path
from typing import Tuple

from django.contrib.gis.geos import GEOSGeometry
from django.core.management.base import BaseCommand
from django.db import transaction
from tqdm import tqdm

from dora.sirene.models import Establishment
from dora.structures.models import Structure, StructureSource, StructureTypology
from dora.users.models import User

logging.basicConfig()
logger = logging.getLogger()


SIAES_FILE_PATH = Path(__file__).parent.parent.parent / "data" / "siaes_08_974.csv"


def normalize_description(desc: str, limit: int) -> Tuple[str, str]:
    if len(desc) < limit:
        return desc, ""
    else:
        return desc[: limit - 3] + "...", desc


def normalize_phone_number(phone: str) -> str:
    ret = phone.replace(" ", "").replace("-", "").replace(".", "")
    if len(ret) < 10:
        return ""
    return ret


def normalize_coords(coords: str) -> Tuple[float, float]:
    pos = GEOSGeometry(coords)
    return pos.x, pos.y


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--log-level", default="INFO", type=str)

    def handle(self, *args, **options):
        logger.setLevel(options["log_level"])

        with open(SIAES_FILE_PATH, newline="") as f:
            data = [row for row in csv.DictReader(f)]

        logger.debug(f"total: {len(data)}")

        antennes = [d for d in data if d["source"] == "USER_CREATED"]
        structures = [d for d in data if d not in antennes]

        structures_by_siret = {
            k: list(g) for k, g in groupby(structures, lambda d: d["siret"])
        }
        antennes_by_asp_id = {
            k: list(g) for k, g in groupby(antennes, lambda d: d["asp_id"])
        }

        logger.debug(f"total antennes: {len(antennes)}")
        logger.debug(f"total structures: {len(structures)}")

        with transaction.atomic():
            bot_user = User.objects.get_dora_bot()
            structure_source, _ = StructureSource.objects.get_or_create(
                value="ITOU", defaults={"label": "Import ITOU"}
            )

            for siret, data in tqdm(
                structures_by_siret.items(), disable=logger.level < logging.INFO
            ):
                if len(data) > 1:
                    # 2 structures mères partagent le même siret
                    logger.debug(f"{siret} has two parent rows. skipping")
                    continue

                datum = data[0]
                establishment = Establishment.objects.filter(siret=siret).first()

                if establishment is None:
                    logger.debug(f"{siret} probably closed. skipping")
                    # structure probablement fermée
                    continue

                structure = Structure.objects.filter(siret=establishment.siret).first()
                if structure is not None:
                    logger.debug(f"{siret} already known. skipping")
                    # structure déjà référencée
                    continue

                # nouvelle structure
                structure = Structure.objects.create_from_establishment(establishment)
                structure.source = structure_source
                structure.creator = bot_user
                structure.last_editor = bot_user
                structure.name = datum["name"]
                structure.email = datum["email"]
                structure.phone = normalize_phone_number(datum["phone"])
                structure.url = datum["website"]
                structure.short_desc, structure.full_desc = normalize_description(
                    datum["description"], limit=Structure.short_desc.field.max_length
                )
                if datum["coords"] != "":
                    structure.longitude, structure.latitude = normalize_coords(
                        datum["coords"]
                    )
                else:
                    structure.longitude, structure.latitude = (
                        establishment.longitude,
                        establishment.latitude,
                    )
                structure.creation_date = datum["created_at"]
                structure.modification_date = datum["updated_at"]
                structure.typology = StructureTypology.objects.get(value=datum["kind"])
                structure.save()

                logger.debug(f"{siret} created")

                # antennes associées
                if "asp_id" in datum and datum["asp_id"] in antennes_by_asp_id:
                    for antenne_datum in antennes_by_asp_id[datum["asp_id"]]:
                        antenne = Structure.objects.create_from_parent_structure(
                            parent=structure,
                            name=antenne_datum["name"],
                            source=structure.source,
                            creator=structure.creator,
                            last_editor=structure.last_editor,
                            address1=antenne_datum["address_line_1"],
                            address2=antenne_datum["address_line_2"],
                            postal_code=antenne_datum["post_code"],
                            city=antenne_datum["city"],
                            email=antenne_datum["email"],
                            phone=normalize_phone_number(antenne_datum["phone"]),
                            url=antenne_datum["website"],
                            typology=StructureTypology.objects.get(value=datum["kind"]),
                            creation_date=antenne_datum["created_at"],
                            modification_date=antenne_datum["updated_at"],
                        )

                        if antenne_datum["description"] != "":
                            (
                                antenne.short_desc,
                                antenne.full_desc,
                            ) = normalize_description(
                                datum["description"],
                                limit=Structure.short_desc.field.max_length,
                            )

                        if antenne_datum["coords"] != "":
                            antenne.longitude, antenne.latitude = normalize_coords(
                                antenne_datum["coords"]
                            )

                        antenne.save()

                        logger.debug(
                            f"{antenne_datum['siret']} created as antenne of {siret}"
                        )
