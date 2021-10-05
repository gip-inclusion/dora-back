from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.db import transaction

from dora.services.models import Service
from dora.structures.models import Structure, StructureTypology
from dora.users.models import User


class Command(BaseCommand):
    help = "Takes one service and duplicates it into all Pole Emploi agencies of a department"

    def add_arguments(self, parser):
        parser.add_argument("service_slug")
        parser.add_argument("department")

    def handle(self, *args, **options):
        slug = options["service_slug"]
        dept = options["department"]
        self.stdout.write(
            self.style.NOTICE(
                f"copying service {slug} to all agencies in department {dept}"
            )
        )

        try:
            source = Service.objects.get(slug=slug)
        except Service.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Service {slug} not found"))

        dests = Structure.objects.filter(
            department=dept, typology=StructureTypology.PE
        ).exclude(id=source.structure_id)
        if not dests.exists():
            self.stderr.write(self.style.ERROR("No destination found"))

        bot_user = User.objects.get_dora_bot()

        with transaction.atomic(durable=True):
            for dest in dests:
                initial_access_conditions = source.access_conditions.all()
                initial_concerned_public = source.concerned_public.all()
                initial_requirements = source.requirements.all()
                initial_credentials = source.credentials.all()

                source.id = None
                source.slug = None
                source.structure = dest
                source.address1 = dest.address1
                source.address2 = dest.address2
                source.postal_code = dest.postal_code
                source.city_code = dest.city_code
                source.city = dest.city
                if dest.longitude and dest.latitude:
                    source.geom = Point(dest.longitude, dest.latitude, srid=4326)
                else:
                    source.geom = None
                source.creation_date = None
                source.modification_date = None
                source.last_editor = bot_user
                source.save()
                source.access_conditions.set(initial_access_conditions)
                source.concerned_public.set(initial_concerned_public)
                source.requirements.set(initial_requirements)
                source.credentials.set(initial_credentials)
                self.stdout.write(self.style.NOTICE(f"Saved to structure {dest.name}"))
        self.stdout.write(self.style.NOTICE("Done"))
