import re
from typing import Dict, List

import requests
from tqdm import tqdm

from django.contrib.postgres.search import TrigramSimilarity
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from dora.services.models import Service, ServiceCategory, ServiceSubCategory
from dora.sirene.models import Establishment
from dora.structures.models import Structure, StructureSource
from dora.users.models import User


class MesAidesClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def list_garages_solidaires(self) -> List[Dict]:
        return requests.get(self.base_url + "/garages-solidaires").json()


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--api_url", default="https://mes-aides.pole-emploi.fr/api/"
        )

    def handle(self, *args, **options):
        data = MesAidesClient(base_url=options["api_url"]).list_garages_solidaires()
        filtered_data = [
            d
            for d in data
            if "norauto" not in d["name"].lower() and "rrg" not in d["name"].lower()
        ]

        with transaction.atomic():
            bot_user = User.objects.get_dora_bot()
            structure_source, _ = StructureSource.objects.get_or_create(
                value="MESAIDES", defaults={"label": "API Mes Aides"}
            )

            for garage_data in tqdm(filtered_data):
                establishment = (
                    Establishment.objects.filter(postal_code=garage_data["zipcode"])
                    .annotate(
                        similarity=TrigramSimilarity(
                            "full_search_text", garage_data["name"]
                        )
                    )
                    .order_by("-similarity")
                    .first()
                )
                if establishment is None:
                    continue

                structure = Structure.objects.filter(siret=establishment.siret).first()
                if structure is not None:
                    continue

                # Nouvelle structure
                structure = Structure.objects.create_from_establishment(establishment)
                structure.source = structure_source
                structure.creator = bot_user
                structure.name = garage_data["name"]
                structure.email = garage_data["email"] or ""
                structure.short_desc = ""
                structure.full_desc = ""
                structure.url = garage_data["url"] or ""
                # garage_data["phone"] peut contenir 2 numéros de téléphone, le 1er est gardé
                structure.phone = "".join(
                    re.findall(r"\d{2}", garage_data["phone"] or "")[:5]
                )
                structure.last_editor = bot_user
                structure.save()

                service = Service.objects.create(
                    name="Garage solidaire",
                    contact_phone=structure.phone,
                    contact_email=structure.email,
                    creator=bot_user,
                    last_editor=bot_user,
                    structure=structure,
                )
                service.categories.add(ServiceCategory.objects.get(value="MO"))
                service.subcategories.add(ServiceSubCategory.objects.get(value="MO-MA"))
