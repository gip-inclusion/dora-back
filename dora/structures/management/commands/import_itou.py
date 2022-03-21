import csv
import logging
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

SIAES_FILE_PATH = (
    Path(__file__).parent.parent.parent / "data" / "prescriber_organizations_08_974.csv"
)


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
    """Commande d'import des données prescribers d'ITOU depuis format csv"""

    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("--log-level", default="INFO", type=str)

    def handle(self, *args, **options):
        logger.setLevel(options["log_level"])

        with open(SIAES_FILE_PATH, newline="") as f:
            data = [row for row in csv.DictReader(f)]

        logger.info(f"{len(data)} lignes en entrée")

        bot_user = User.objects.get_dora_bot()
        structure_source, _ = StructureSource.objects.get_or_create(
            value="ITOU", defaults={"label": "Import ITOU"}
        )

        known_structures = []
        unknown_sirets = []
        new_structures = []

        with transaction.atomic():
            for datum in tqdm(data, disable=logger.level < logging.INFO):
                if (
                    "code_safir_pole_emploi" in datum
                    and Structure.objects.filter(
                        code_safir_pe=datum["code_safir_pole_emploi"]
                    ).exists()
                ):
                    # code saphir déjà référencé
                    logger.debug(
                        f"code_saphir={datum['code_safir_pole_emploi']} déjà référencé. Ignoré"
                    )
                    known_structures.append(datum)
                    continue

                try:
                    establishment = Establishment.objects.get(siret=datum["siret"])
                except Establishment.DoesNotExist:
                    # siret invalide
                    logger.debug(f"{datum['siret']} n'existe pas")

                    # tentative d'identification du siret à partir du siren
                    # si l'entreprise n'a qu'un seul établissement
                    try:
                        establishment = Establishment.objects.get(
                            siren=datum["siret"][:9]
                        )
                    except Establishment.MultipleObjectsReturned:
                        # plusieurs établissement pour ce siren
                        unknown_sirets.append(datum)
                        continue
                    except Establishment.DoesNotExist:
                        # siren invalide
                        unknown_sirets.append(datum)
                        continue

                    logger.debug(
                        f"{datum['siret']} -> {establishment.siret} unique établissement pour siren"
                    )

                structure = Structure.objects.filter(siret=establishment.siret).first()
                if structure is not None:
                    known_structures.append(datum)
                    logger.debug(f"{establishment.siret} déjà référencé. Ignoré")
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

                logger.debug(f"{establishment.siret} nouvellement référencé")
                new_structures.append(structure)

            logger.info(f"{len(unknown_sirets)} sirets inconnus")
            logger.info(f"{len(known_structures)} sirets déjà référencés")
            logger.info(f"{len(new_structures)} nouvelles structures")
