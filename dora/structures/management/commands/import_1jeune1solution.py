import enum
import logging
import re
from itertools import groupby
from typing import Dict, List, Optional, Union

import requests
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction
from tqdm import tqdm

from dora.admin_express.models import Department, Region
from dora.admin_express.utils import normalize_string_for_search
from dora.sirene.models import Establishment
from dora.structures.models import Structure, StructureSource, StructureTypology
from dora.users.models import User

logging.basicConfig()
logger = logging.getLogger()


class APE(str, enum.Enum):
    ADMIN_PUB_GEN = "84.11Z"
    ACTION_SOCIAL_SANS_H = "88.99B"
    ENSEIGNEMENT_2ND_GEN = "85.31Z"
    ADMIN_PUB_SANTE_SOCIAL = "84.12Z"
    ADMIN_AE = "84.13Z"
    ASSO = "94.99Z"
    DISTRIB_SOC_REV = "84.30C"
    ACTI_GEN_SECU_SOC = "84.30A"


class InstitutionType(str, enum.Enum):
    REGION = "region"
    DEPARTEMENT = "departement"
    COMMUNE = "commune"
    CAF = "caf"
    EPCI = "epci"
    NATIONAL = "national"


class UnJeuneUneSolutionClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def list_benefits(self) -> List[Dict]:
        return requests.get(self.base_url + "/benefits").json()


TYPOLOGY_BY_INSTITUTION_TYPE = {
    "caf": "CAF",
    "region": "REG",
    "national": None,
    "commune": "MUNI",
    "epci": "EPCI",
    "departement": "DEPT",
}


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--log-level", default="INFO", type=str)
        parser.add_argument(
            "--api_url", default="https://mes-aides.1jeune1solution.beta.gouv.fr/api/"
        )

    def handle(self, *args, **options):
        logger.setLevel(options["log_level"])

        client = UnJeuneUneSolutionClient(base_url=options["api_url"])
        benefits_data = client.list_benefits()

        logger.info(f"{len(benefits_data)} benefits en entrée")

        bot_user = User.objects.get_dora_bot()
        structure_source = StructureSource.objects.get(value="api-1jeune1solution")

        benefits_by_institution_id = {
            k: list(g)
            for k, g in groupby(benefits_data, lambda d: d["institution"]["id"])
        }
        institutions_by_id = {
            k: {**v[0]["institution"], "benefits": v}
            for k, v in benefits_by_institution_id.items()
        }

        unidentifiables = []
        known_structures = []
        new_structures = []

        logger.info(f"{len(institutions_by_id)} institutions en entrée")

        establishment_by_institution_id = {
            d["id"]: identify_establishment(d)
            for d in tqdm(institutions_by_id.values(), desc="Identification")
        }

        with transaction.atomic():
            for datum in tqdm(
                institutions_by_id.values(),
                disable=logger.level < logging.INFO,
                desc="Création",
            ):
                establishment = establishment_by_institution_id[datum["id"]]

                if establishment is None:
                    logger.debug(f"{datum['id']} n'a pas pu être identifié. Ignoré")
                    unidentifiables.append(datum)
                    continue

                structure = Structure.objects.filter(siret=establishment.siret).first()
                if structure is not None:
                    logger.debug(f"{structure.siret} déjà référencé. Ignoré")
                    known_structures.append(datum)
                    continue

                # nouvelle structure
                structure = Structure.objects.create_from_establishment(establishment)
                structure.source = structure_source
                structure.creator = bot_user
                structure.last_editor = bot_user
                structure.name = datum["label"] if "label" in datum else None
                structure.longitude, structure.latitude = (
                    establishment.longitude,
                    establishment.latitude,
                )
                # TODO(vmttn): reprendre leur slug ?
                structure.typology = StructureTypology.objects.get(
                    value=TYPOLOGY_BY_INSTITUTION_TYPE[datum["type"]]
                )
                structure.save()

                logger.debug(
                    f"{datum['id']} -> {structure.siret} nouvellement référencé"
                )
                new_structures.append(datum)

        logger.info(f"{len(unidentifiables)} entrées non identifiables")
        logger.info(f"{len(known_structures)} sirets déjà référencés")
        logger.info(f"{len(new_structures)} nouvelles structures")


def admin_from_name(name: str, type: InstitutionType) -> Union[Department, Region]:
    model_by_institution_type = {
        InstitutionType.REGION: Region,
        InstitutionType.DEPARTEMENT: Department,
    }
    model = model_by_institution_type[type]
    return model.objects.get(normalized_name=normalize_string_for_search(name))


def identify_establishment(institution_data: Dict) -> Optional[Establishment]:
    # tentative d'identification via siren
    if siren := institution_data.get("code_siren", None):
        ret = Establishment.objects.filter(is_siege=True).filter(siren=siren).first()
        if ret is not None:
            return ret

    # tentative d'identification via localisation et type
    institution_type = institution_data.get("type", None)
    if institution_type == InstitutionType.COMMUNE:
        code_insee = institution_data.get("code_insee", None)
        if code_insee is not None:
            qs = (
                Establishment.objects.filter(is_siege=True)
                .filter(city_code=code_insee)
                .filter(ape=APE.ADMIN_PUB_GEN.value)
                .filter(name__icontains="mairie")
                .all()
            )
            if len(qs) == 1:
                return qs.first()
    elif institution_type == InstitutionType.CAF:
        department = admin_from_name(
            re.match(
                r"CAF .*?(?P<department_str>[A-Z].*)", institution_data["label"]
            ).groupdict()["department_str"],
            type=InstitutionType.DEPARTEMENT,
        )
        qs = (
            Establishment.objects.filter(is_siege=True)
            .filter(city_code__startswith=department.code)
            .filter(name__iregex=r"caf")
            .filter(name__iregex=r"allocations? familiales?")
            .filter(name__iregex=rf"{department.normalized_name}")
            .all()
        )
        if len(qs) == 1:
            return qs.first()
    elif institution_type == InstitutionType.DEPARTEMENT:
        return Establishment.objects.get(
            siret=SIRET_BY_DEPARTEMENT_CODE[institution_data["code_insee"]]
        )
    elif institution_type == InstitutionType.REGION:
        return Establishment.objects.get(
            siret=SIRET_BY_REGION_CODE[institution_data["code_insee"]]
        )
    elif institution_type == InstitutionType.EPCI:
        return None
    elif institution_type == InstitutionType.NATIONAL:
        return None

    return None


SIRET_BY_REGION_CODE = {
    "973": "20005267800014",
    "94": "20007695800012",  # COLLECTIVITE DE CORSE
    "03": "20005267800014",  # COLLECTIVITE TERRITORIALE DE GUYANE
    "02": "20005550700012",  # COLLECTIVITE TERRITORIALE DE MARTINIQUE
    "01": "23971001500029",  # CONSEIL REGIONAL DE LA GUADELOUPE
    "06": "22985000300018",  # DEPARTEMENT DE MAYOTTE
    "84": "20005376700014",  # REGION AUVERGNE-RHONE-ALPES
    "27": "20005372600028",  # REGION BOURGOGNE-FRANCHE-COMTE HOTEL DE REGION
    "53": "23350001600040",  # REGION BRETAGNE CONSEIL REGIONAL
    "24": "23450002300028",  # REGION CENTRE-VAL DE LOIRE
    "52": "23440003400026",  # REGION DES PAYS DE LA LOIRE CONSEIL REGIONAL DES PAYS DE LA LOIRE
    "44": "20005226400013",  # REGION GRAND EST
    "32": "20005374200017",  # REGION HAUTS-DE-FRANCE
    "11": "23750007900312",  # REGION ILE DE FRANCE
    "28": "20005340300057",  # REGION NORMANDIE HOTEL DE REGION
    "75": "20005375900011",  # REGION NOUVELLE-AQUITAINE
    "76": "20005379100014",  # REGION OCCITANIE
    "93": "23130002100012",  # REGION PROVENCE-ALPES-COTE D'AZUR CONSEIL REGIONAL P.A.C.A
    "04": "23974001200012",  # REGION REUNION CONSEIL REGIONAL
}

SIRET_BY_DEPARTEMENT_CODE = {
    "01": "22010001000010",  # DEPARTEMENT DE L AIN
    "02": "22020002600015",  # DEPARTEMENT DE L AISNE
    "03": "22030001600080",  # DEPARTEMENT DE L ALLIER
    "04": "22040001400019",  # DEPARTEMENT DES ALPES DE HAUTE PROVENCE
    "05": "22050001100089",  # DEPARTEMENT DES HAUTES ALPES
    "06": "22060001900016",  # DEPARTEMENT DES ALPES MARITIMES
    "07": "22070001700019",  # DEPARTEMENT DE L ARDECHE
    "08": "22080004900011",  # DEPARTEMENT DES ARDENNES
    "09": "22090001300016",  # DEPARTEMENT DE L ARIEGE
    "10": "22100005200011",  # DEPARTEMENT DE L AUBE
    "11": "22110001900019",  # DEPARTEMENT DE L AUDE
    "12": "22120001700012",  # DEPARTEMENT DE L AVEYRON
    "13": "22130001500247",  # DEPARTEMENT DES BOUCHES DU RHONE
    "14": "22140118500014",  # DEPARTEMENT DU CALVADOS
    "15": "22150001000014",  # DEPARTEMENT DU CANTAL
    "16": "22160001800016",  # DEPARTEMENT DE LA CHARENTE
    "17": "22170001600738",  # DEPARTEMENT DE LA CHARENTE-MARITIME
    "18": "22180001400013",  # DEPARTEMENT DU CHER
    "19": "22192720500197",  # DEPARTEMENT DE LA CORREZE
    "2A": "20007695800012",  # COLLECTIVITE DE CORSE TODO(vmttn): à valider
    "2B": "20007695800012",  # COLLECTIVITE DE CORSE TODO(vmttn): à valider
    "21": "22210001800019",  # DEPARTEMENT DE COTE D OR
    "22": "22220001600327",  # DEPARTEMENT DES COTES D'ARMOR
    "23": "22230962700016",  # DEPARTEMENT DE LA CREUSE
    "24": "22240001200019",  # DEPARTEMENT DE LA DORDOGNE
    "25": "22250001900013",  # DEPARTEMENT DU DOUBS
    "26": "22260001700016",  # DEPARTEMENT DE LA DROME
    "27": "22270229200012",  # DEPARTEMENT DE L EURE
    "28": "22280001300013",  # DEPARTEMENT DE L'EURE ET LOIR
    "29": "22290001100016",  # DEPARTEMENT DU FINISTERE
    "30": "22300001900073",  # DEPARTEMENT DU GARD
    "31": "22310001700423",  # DEPARTEMENT DE LA HAUTE GARONNE
    "32": "22320001500012",  # DEPARTEMENT DU GERS
    "33": "22330001300016",  # DEPARTEMENT DE LA GIRONDE
    "34": "22340001100076",  # DEPARTEMENT DE L HERAULT
    "35": "22350001800013",  # DEPARTEMENT D ILLE ET VILAINE
    "36": "22360001600016",  # DEPARTEMENT DE L'INDRE
    "37": "22370001400010",  # DEPARTEMENT DE L'INDRE ET LOIRE
    "38": "22380001200013",  # DEPARTEMENT DE L ISERE
    "39": "22390001000362",  # DEPARTEMENT DU JURA
    "40": "22400001800016",  # DEPARTEMENT DES LANDES
    "41": "22410001600019",  # DEPARTEMENT DU LOIR ET CHER
    "42": "22420001400013",  # DEPARTEMENT DE LA LOIRE
    "43": "22430001200016",  # DEPARTEMENT DE LA HAUTE LOIRE
    "44": "22440002800011",  # DEPARTEMENT DE LA LOIRE-ATLANTIQUE
    "45": "22450001700013",  # DEPARTEMENT DU LOIRET
    "46": "22460001500511",  # DEPARTEMENT DU LOT
    "47": "22470001300424",  # DEPARTEMENT DU LOT ET GARONNE
    "48": "22480001100013",  # DEPARTEMENT DE LA LOZERE
    "49": "22490001900015",  # DEPARTEMENT DE MAINE ET LOIRE CONSEIL DEPARTEMENTAL
    "50": "22500502400081",  # DEPARTEMENT DE LA MANCHE
    "51": "22510001500018",  # DEPARTEMENT DE LA MARNE
    "52": "22520001300012",  # DEPARTEMENT DE LA HAUTE-MARNE
    "53": "22530001100015",  # DEPARTEMENT DE LA MAYENNE
    "54": "22540001900785",  # DEPARTEMENT DE MEURTHE ET MOSELLE
    "55": "22550001600152",  # DEPARTEMENT DE LA MEUSE
    "56": "22560001400016",  # DEPARTEMENT DU MORBIHAN
    "57": "22570001200019",  # DEPARTEMENT DE LA MOSELLE
    "58": "22580001000012",  # DEPARTEMENT DE LA NIEVRE
    "59": "22590001801244",  # DEPARTEMENT DU NORD
    "60": "22600001600403",  # DEPARTEMENT DE L'OISE
    "61": "22610001400134",  # DEPARTEMENT DE L'ORNE
    "62": "22620001200012",  # DEPARTEMENT DU PAS DE CALAIS
    "63": "22630001000015",  # DEPARTEMENT DU PUY DE DOME
    "64": "22640001800876",  # DEPARTEMENT DES PYRENEES ATLANTIQUES
    "65": "22650001500012",  # DEPARTEMENT DES HAUTES PYRENEES
    "66": "22660001300016",  # DEPARTEMENT DES PYRENEES-ORIENTALES
    "6AE": "20009433200018",  # COLLECTIVITE EUROPEENE D'ALSACE (67 et 68)
    "69": "22690001700014",  # DEPARTEMENT DU RHONE
    "70": "22700001500015",  # DEPARTEMENT DE HAUTE SAONE
    "71": "22710001300688",  # DEPARTEMENT DE SAONE ET LOIRE
    "72": "22720002900014",  # DEPARTEMENT DE LA SARTHE
    "73": "22730001900014",  # DEPARTEMENT DE LA SAVOIE
    "74": "22740001700074",  # DEPARTEMENT DE LA HAUTE SAVOIE
    "75": "21750001600019",  # VILLE DE PARIS
    "76": "22760540900019",  # DEPARTEMENT DE LA SEINE MARITIME
    "77": "22770001000019",  # DEPARTEMENT DE SEINE ET MARNE
    "78": "22780646000019",  # DEPARTEMENT DES YVELINES
    "79": "22790001600352",  # DEPARTEMENT DES DEUX SEVRES
    "80": "22800001400016",  # DEPARTEMENT DE LA SOMME
    "81": "22810001200019",  # DEPARTEMENT DU TARN
    "82": "22820001000012",  # DEPARTEMENT DU TARN ET GARONNE
    "83": "22830001800113",  # DEPARTEMENT DU VAR
    "84": "22840001600017",  # DEPARTEMENT DU VAUCLUSE
    "85": "22850001300658",  # DEPARTEMENT DE VENDEE
    "86": "22860001100016",  # DEPARTEMENT DE LA VIENNE
    "87": "22870851700989",  # DEPARTEMENT DE LA HAUTE VIENNE
    "88": "22880001700011",  # DEPARTEMENT DES VOSGES
    "89": "22890001500238",  # DEPARTEMENT DE L'YONNE
    "90": "22900001300040",  # DEPARTEMENT DU TERRITOIRE DE BELFORT
    "91": "22910228000018",  # DEPARTEMENT DE L' ESSONNE
    "92": "22920050600611",  # DEPARTEMENT DES HAUTS-DE-SEINE
    "93": "22930008201453",  # DEPARTEMENT DE LA SEINE SAINT DENIS
    "94": "22940028800010",  # DEPARTEMENT DU VAL DE MARNE
    "95": "22950127500015",  # DEPARTEMENT DU VAL D OISE
    "971": "22971001700018",  # DEPARTEMENT DE LA GUADELOUPE CONSEIL DEPARTEMENTAL
    "972": "20005550700012",  # COLLECTIVITE TERRITORIALE DE MARTINIQUE
    "973": "20005267800014",  # COLLECTIVITE TERRITORIALE DE GUYANE
    "974": "22974001400019",  # DEPARTEMENT DE LA REUNION
    "976": "22985000300018",  # DEPARTEMENT DE MAYOTTE
}
