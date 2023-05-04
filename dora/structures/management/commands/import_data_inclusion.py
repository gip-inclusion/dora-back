import json

import requests
from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import Truncator
from furl import furl

from dora.admin_express.models import AdminDivisionType
from dora.core import utils
from dora.core.models import ModerationStatus
from dora.core.notify import send_moderation_notification
from dora.core.utils import normalize_description
from dora.services.enums import ServiceStatus
from dora.services.models import (
    ConcernedPublic,
    Credential,
    LocationKind,
    Requirement,
    Service,
    ServiceCategory,
    ServiceFee,
    ServiceKind,
    ServiceSource,
    ServiceSubCategory,
)
from dora.sirene.models import Establishment
from dora.structures.models import (
    Structure,
    StructureNationalLabel,
    StructureSource,
    StructureTypology,
)
from dora.users.models import User

# Documentation DI : https://data-inclusion-api-prod.osc-secnum-fr1.scalingo.io/api/v0/docs

BASE_URL = furl(settings.DATA_INCLUSION_URL)

STRUCTURES_INDEX = {}


def clean_field(value, max_length, default_value):
    if not value:
        return default_value
    return Truncator(value).chars(max_length)


class Command(BaseCommand):
    help = "Importe les nouvelles structures Data Inclusion qui n'existent pas encore dans Dora"

    def add_arguments(self, parser):
        parser.add_argument("source", type=str)
        parser.add_argument("--department", type=str)

    def handle(self, *args, **options):
        department = options["department"]
        source = options["source"]

        self.stdout.write(self.style.SUCCESS(f"Import de la source: {source}"))
        try:
            structures = self.get_structures(source, department)
            self.import_structures(source, structures)
            services = self.get_services(source, department)
            self.import_services(source, services)
        except requests.exceptions.RequestException as e:
            self.stderr.write(self.style.ERROR(e))

    def get_structures(self, source, department):
        structures = []
        args = {"source": source, "size": 100}
        if department:
            args["departement"] = department

        url = BASE_URL.copy().add(
            path="structures/",
            args=args,
        )

        for results in self.get_pages(url):
            structures += results

        return structures

    def get_services(self, source, department):
        services = []
        args = {"source": source, "size": 100}
        if department:
            args["departement"] = department

        url = BASE_URL.copy().add(
            path="services/",
            args=args,
        )

        for results in self.get_pages(url):
            services += results

        return services

    def get_pages(self, url):
        page = 1
        while True:
            paginated_url = url.copy().add({"page": page})
            self.stdout.write(f"Chargement de {paginated_url}")
            response = requests.get(
                paginated_url,
                params={},
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": f"Bearer {settings.DATA_INCLUSION_API_KEY}",
                },
            )
            if response.status_code != 200:
                self.stderr.write(
                    self.style.ERROR(
                        f"Erreur dans la récupération des données\n{url}: {response.status_code}"
                    )
                )
                return

            result = json.loads(response.content)["items"]
            if len(result):
                yield result
                page += 1
            else:
                return

    def import_structures(self, source_value, structures):
        bot_user = User.objects.get_dora_bot()
        source, _created = StructureSource.objects.get_or_create(
            value=f"di-{source_value}",
            defaults={"label": source_value},
        )
        if _created:
            self.stdout.write(
                self.style.ERROR(
                    f"Source: di-{source_value} inexistante. Pensez à renseigner son label dans l'interface "
                    f"d'administration"
                )
            )
        num_imported = 0

        for s in structures:
            if not s["siret"]:
                continue
            STRUCTURES_INDEX[s["id"]] = s["siret"]
            matched_structures = Structure.objects.filter(siret=s["siret"])
            if matched_structures.exists():
                # la structure existe déjà; on ne la traite pas, mais on récupère l'id data·inclusion
                # si nécessaire
                parent = matched_structures.filter(
                    parent=None, data_inclusion_id=None
                ).first()
                if parent:
                    self.stdout.write(
                        self.style.NOTICE(
                            f"Mise à jour de l'id data·inclusion pour : {parent.slug}"
                        )
                    )
                    parent.data_inclusion_id = s["id"]
                    parent.save()
                continue
            try:
                establishment = Establishment.objects.get(siret=s["siret"])
            except Establishment.DoesNotExist:
                self.stdout.write(
                    self.style.NOTICE(
                        f"Siret incorrect, ignoré : {s['siret']} ({s['nom']})"
                    )
                )
                continue
            try:
                typology = None
                if s["typologie"]:
                    typology, _created = StructureTypology.objects.get_or_create(
                        value=s["typologie"]
                    )
                if _created:
                    self.stdout.write(
                        self.style.ERROR(
                            f"typology: {s['typologie']} inexistante. Pensez à renseigner son label dans l'interface "
                            f"d'administration"
                        )
                    )
                structure = Structure.objects.create(
                    data_inclusion_id=s["id"],
                    siret=s["siret"],
                    name=clean_field(s["nom"], 255, establishment.name),
                    address1=clean_field(s["adresse"], 255, establishment.address1),
                    address2=clean_field(
                        s["complement_adresse"], 255, establishment.address2
                    ),
                    city_code=s["code_insee"] or establishment.city_code,
                    postal_code=s["code_postal"] or establishment.postal_code,
                    city=clean_field(s["commune"], 255, establishment.city),
                    latitude=s["latitude"] or establishment.latitude,
                    longitude=s["longitude"] or establishment.longitude,
                    email=clean_field(s["courriel"], 254, ""),
                    phone=utils.normalize_phone_number(s["telephone"] or ""),
                    url=clean_field(s["site_web"], 200, ""),
                    full_desc=s["presentation_detail"] or "",
                    short_desc=clean_field(s["presentation_resume"], 280, ""),
                    typology=typology,
                    accesslibre_url=s["accessibilite"],
                    ape=establishment.ape,
                    source=source,
                    creator=bot_user,
                    last_editor=bot_user,
                    modification_date=timezone.now(),
                )
                for label in s["labels_nationaux"] or []:
                    new_label, _created = StructureNationalLabel.objects.get_or_create(
                        value=label
                    )
                    if _created:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Label national: {label} inexistant. Pensez à le compléter dans l'interface "
                                f"d'administration"
                            )
                        )
                    structure.national_labels.add(new_label)

                send_moderation_notification(
                    structure,
                    bot_user,
                    f"Structure importée de Data Inclusion ({source})",
                    ModerationStatus.VALIDATED,
                )
                num_imported += 1

            except Exception as e:
                print(s)
                self.stderr.write(s)
                self.stderr.write(self.style.ERROR(e))
        self.stdout.write(self.style.SUCCESS(f"{num_imported} structures importées"))

    def import_services(self, source_value, services):
        def cust_choice_to_objects(Model, values):
            if values:
                return Model.objects.filter(name__in=values)
            return []

        bot_user = User.objects.get_dora_bot()
        source, _created = ServiceSource.objects.get_or_create(
            value=f"di-{source_value}",
            defaults={"label": source_value},
        )
        if _created:
            self.stdout.write(
                self.style.ERROR(
                    f"Source: di-{source_value} inexistante. Pensez à renseigner son label dans l'interface "
                    f"d'administration"
                )
            )
        num_imported = 0
        for s in services:
            if Service.objects.filter(data_inclusion_id=s["id"]).exists():
                continue
            siret = STRUCTURES_INDEX.get(s["structure_id"])
            if not siret:
                self.style.ERROR(f"Impossible de trouver le siret correspondant à {s}")
                continue

            structures = Structure.objects.filter(siret=siret)
            if not structures:
                self.stdout.write(
                    self.style.ERROR(
                        f"La structure correspondant au service {s['id']}, de siret {siret}, n'a pas été créée"
                    )
                )
                continue
            if len(structures) > 1:
                main_structures = structures.filter(parent=None)
                if main_structures:
                    structures = main_structures

            structure = structures[0]
            try:
                service = Service.objects.create(
                    data_inclusion_id=s["id"],
                    structure=structure,
                    name=s["nom"],
                    short_desc=s["presentation_resume"] or "",
                    full_desc=s["presentation_detail"] or "",
                    fee_details=s["frais_autres"] or "",
                    is_cumulative=False if s["cumulable"] is False else True,
                    online_form=s["formulaire_en_ligne"] or "",
                    city=s["commune"] or "",
                    postal_code=s["code_postal"] or "",
                    city_code=s["code_insee"] or "",
                    address1=s["adresse"] or "",
                    address2=s["complement_adresse"] or "",
                    recurrence=s["recurrence"] or "",
                    suspension_date=s["date_suspension"],
                    contact_phone=s["telephone"] or "",
                    contact_email=s["courriel"] or "",
                    is_contact_info_public=s["contact_public"] is True,
                    diffusion_zone_type=s["zone_diffusion_type"] or "",
                    diffusion_zone_details=s["zone_diffusion_code"] or "",
                    source=source,
                    creator=bot_user,
                    last_editor=bot_user,
                    modification_date=timezone.now(),
                )
                lon = s["longitude"]
                lat = s["latitude"]

                if lon and lat:
                    service.geom = Point(lon, lat, srid=4326)

                service.status = ServiceStatus.PUBLISHED
                service.concerned_public.set(
                    cust_choice_to_objects(ConcernedPublic, s["profils"])
                )
                service.requirements.set(
                    cust_choice_to_objects(Requirement, s["pre_requis"])
                )
                service.credentials.set(
                    cust_choice_to_objects(Credential, s["justificatifs"])
                )

                subcats = s["thematiques"]
                cats = [s.split("--")[0] for s in subcats]
                service.categories.set(self._values_to_objects(ServiceCategory, cats))
                service.subcategories.set(
                    self._values_to_objects(ServiceSubCategory, subcats)
                )

                service.kinds.set(self._values_to_objects(ServiceKind, s["types"]))
                service.fee_condition = ServiceFee.objects.filter(
                    value__in=s["frais"]
                ).first()
                service.location_kinds.set(
                    self._values_to_objects(LocationKind, s["modes_accueil"])
                )
                if source_value.startswith("mediation-numerique"):
                    self._presave_mednum_services(service)
                service.save()
                send_moderation_notification(
                    service,
                    bot_user,
                    f"Structure importée de Data Inclusion ({source})",
                    ModerationStatus.VALIDATED,
                )
                num_imported += 1

            except Exception as e:
                print(e)
                print(s)
                self.stderr.write(s)
                self.stderr.write(self.style.ERROR(e))
                continue
        self.stdout.write(self.style.SUCCESS(f"{num_imported} services importés"))

    def _values_to_objects(self, Model, values):
        if values:
            return Model.objects.filter(value__in=values)
        return []

    def _presave_mednum_services(self, service):
        service.use_inclusion_numerique_scheme = True
        if not service.short_desc:
            subcats_label = ", ".join(
                s.label.lower() for s in service.subcategories.all()
            )
            short_desc, _ = normalize_description(subcats_label, 280)
            service.short_desc = (
                f"{service.structure.name} propose des services : {short_desc}"
            )
        if not service.address1 or not service.postal_code or not service.city_code:
            service.address1 = service.structure.address1
            service.address2 = service.structure.address2
            service.postal_code = service.structure.postal_code
            service.city_code = service.structure.city_code
            service.city = service.structure.city
        if not service.geom:
            lon = service.structure.longitude
            lat = service.structure.latitude
            if lon and lat:
                service.geom = Point(lon, lat, srid=4326)
        if not service.contact_email:
            service.contact_email = service.structure.email
        if not service.contact_phone:
            service.contact_phone = service.structure.phone
        if not service.location_kinds:
            service.location_kinds.set(
                self._values_to_objects(LocationKind, "en-presentiel")
            )
        if service.structure.department and (
            not service.diffusion_zone_type or not service.diffusion_zone_details
        ):
            service.diffusion_zone_type = AdminDivisionType.DEPARTMENT
            service.diffusion_zone_details = service.structure.department
