import csv
import logging
from pathlib import Path
from typing import Tuple

from django.contrib.gis.geos import GEOSGeometry
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models.expressions import RawSQL
from tqdm import tqdm

from dora.sirene.models import Establishment
from dora.structures import utils
from dora.structures.models import Structure, StructureSource, StructureTypology
from dora.users.models import User

logging.basicConfig()
logger = logging.getLogger()

SIREN_POLE_EMPLOI = "130005481"


def hexewkb_str_to_lonlat(geom: str) -> Tuple[float, float]:
    pos = GEOSGeometry(geom)
    return pos.x, pos.y


class Command(BaseCommand):
    """Commande d'import des données organisations d'ITOU depuis format csv

    Les données prescribers ITOU contiennent soit des données avec SIRET,
    soit des données de structures type pole emploi (pas exclusivement des agences).
    """

    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("--log-level", default="INFO", type=str)
        parser.add_argument("input_path", type=Path)

    def handle(self, *args, **options):
        logger.setLevel(options["log_level"])

        with open(options["input_path"], newline="") as f:
            data = [row for row in csv.DictReader(f)]

        logger.info(f"{len(data)} lignes en entrée")

        bot_user = User.objects.get_dora_bot()
        structure_source = StructureSource.objects.get(value="ITOU")

        known_structures = []
        unidentifiables = []
        new_structures = []

        with transaction.atomic():
            for datum in tqdm(data, disable=logger.level < logging.INFO):
                # ignore les Pole Emploi déjà référencés
                if (
                    datum["code_safir_pole_emploi"] != ""
                    and Structure.objects.filter(
                        code_safir_pe=datum["code_safir_pole_emploi"]
                    ).exists()
                ):
                    logger.debug(
                        f"code_safir={datum['code_safir_pole_emploi']} déjà référencé. "
                        "Ignoré"
                    )
                    known_structures.append(datum)
                    continue

                establishment = None

                # tentative d'identification via siret/siren
                if datum["siret"] != "":
                    establishment = Establishment.objects.filter(
                        siret=datum["siret"]
                    ).first()

                    if establishment is None:
                        # siret invalide
                        logger.debug(f"{datum['siret']} n'existe pas")

                        # tentative d'identification du siret à partir du siren
                        # si l'entreprise n'a qu'un seul établissement
                        try:
                            establishment = Establishment.objects.get(
                                siren=datum["siret"][:9]
                            )
                            logger.debug(
                                f"{datum['siret']} -> {establishment.siret} unique "
                                "établissement pour siren"
                            )
                        except Establishment.MultipleObjectsReturned:
                            # plusieurs établissement pour ce siren
                            pass
                        except Establishment.DoesNotExist:
                            # siren invalide
                            unidentifiables.append(datum)
                            continue

                # tentative d'identification des pole emplois via proximité géographique
                if (
                    establishment is None
                    and datum["code_safir_pole_emploi"] != ""
                    and datum["coords"] != ""
                ):
                    establishment = (
                        Establishment.objects.filter(siren=SIREN_POLE_EMPLOI)
                        .filter(postal_code__startswith=datum["post_code"][:2])
                        .annotate(
                            distance=RawSQL(
                                "ST_Distance(ST_SetSRID(ST_MakePoint(longitude, latitude), 4326), %s)",
                                params=[datum["coords"]],
                            )
                        )
                        .filter(distance__lt=0.001)
                        .order_by("distance")
                        .first()
                    )
                    logger.debug(
                        f"{establishment.siret}, PE identifié par proximité "
                        f"géographique (safir={datum['code_safir_pole_emploi']})"
                    )

                if establishment is None:
                    logger.debug(
                        f"(id={datum['id']},siret={datum['siret']}, "
                        f"safir={datum['code_safir_pole_emploi']}) non identifiable"
                    )
                    unidentifiables.append(datum)
                    continue

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
                structure.phone = utils.normalize_phone_number(datum["phone"])
                structure.url = datum["website"]
                structure.short_desc, structure.full_desc = utils.normalize_description(
                    datum["description"], limit=Structure.short_desc.field.max_length
                )
                if datum["coords"] != "":
                    structure.longitude, structure.latitude = hexewkb_str_to_lonlat(
                        datum["coords"]
                    )
                    if (
                        datum["geocoding_score"] is not None
                        and datum["geocoding_score"] != ""
                    ):
                        structure.geocoding_score = float(datum["geocoding_score"])
                else:
                    structure.longitude, structure.latitude = (
                        establishment.longitude,
                        establishment.latitude,
                    )
                structure.modification_date = datum["updated_at"]
                structure.typology = StructureTypology.objects.get(value=datum["kind"])
                structure.save()

                logger.debug(f"{establishment.siret} nouvellement référencé")
                new_structures.append(structure)

        logger.info(f"{len(unidentifiables)} entrées non identifiables")
        logger.info(f"{len(known_structures)} sirets déjà référencés")
        logger.info(f"{len(new_structures)} nouvelles structures")
