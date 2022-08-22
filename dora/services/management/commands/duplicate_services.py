import sys

from django.core.management.base import BaseCommand
from django.db import transaction

from dora.services.models import ServiceModel
from dora.services.utils import instantiate_model
from dora.structures.models import Structure
from dora.users.models import User


class Command(BaseCommand):
    help = "Takes one model and duplicates it into a list of structures"

    def add_arguments(self, parser):
        parser.add_argument("service_slug")
        parser.add_argument("structures_slugs", nargs="*")

    def handle(self, *args, **options):
        service_slug = options["service_slug"]
        structures_slugs = options["structures_slugs"]
        try:
            source = ServiceModel.objects.get(slug=service_slug)
        except ServiceModel.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Modèle {service_slug} not found"))
            sys.exit(1)

        structures = Structure.objects.filter(slug__in=structures_slugs).exclude(
            id=source.structure_id
        )
        if not structures.exists():
            self.stderr.write(self.style.ERROR("No destination found"))
            sys.exit(1)

        bot_user = User.objects.get_dora_bot()
        with transaction.atomic(durable=True):
            for structure in structures:
                clone = instantiate_model(source, structure, bot_user)
                self.stdout.write(
                    self.style.NOTICE(
                        f"Copied to structure {structure.name}: {clone.get_frontend_url()}"
                    )
                )
        self.stdout.write(self.style.NOTICE("Done"))
