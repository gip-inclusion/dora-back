import csv

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import Truncator

from dora.core import utils
from dora.core.models import ModerationStatus
from dora.core.notify import send_moderation_notification
from dora.rest_auth.models import Token
from dora.services.enums import ServiceStatus
from dora.services.models import Service, ServiceKind
from dora.sirene.models import Establishment
from dora.structures.emails import send_invitation_email
from dora.structures.models import (
    Structure,
    StructureMember,
    StructurePutativeMember,
    StructureSource,
    StructureTypology,
)
from dora.users.models import User


def find_siret(name, postcode, sirets):
    for line in sirets:
        if line[1] == name and line[3] == postcode:
            return line[0]


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("data_filename")
        parser.add_argument("sirets_filename")

    def handle(self, *args, **options):
        data_filename = options["data_filename"]
        sirets_filename = options["sirets_filename"]
        bot_user = User.objects.get_dora_bot()

        with open(sirets_filename) as sirets_file:
            sirets = list(csv.reader(sirets_file, delimiter=","))
        sirets = sirets[1:]

        with open(data_filename) as data_file:
            data = list(csv.reader(data_file, delimiter=","))

        data = data[1:]

        for raw_line in data:
            line = [cell.strip() for cell in raw_line]
            modified = False
            siret = find_siret(line[1], line[3], sirets)
            if not siret:
                self.stdout.write(f"Pas de siret pour {line[0]}")
                continue
            try:
                structure = Structure.objects.get(siret=siret)
            except Structure.DoesNotExist:
                try:
                    establishment = Establishment.objects.get(siret=siret)
                except Establishment.DoesNotExist:
                    self.stdout.write(f"Siret incorrect: {siret}")
                    continue

                structure = Structure.objects.create_from_establishment(establishment)
                modified = True

                structure.creator = bot_user
                structure.source = StructureSource.objects.get(
                    value="invitations-masse"
                )
                send_moderation_notification(
                    structure,
                    bot_user,
                    "Structure créée à partir d'une invitation en masse",
                    ModerationStatus.VALIDATED,
                )

            if not structure.typology:
                typology = StructureTypology.objects.get(label=line[6])
                if typology:
                    structure.typology = typology
                    modified = True
            if not structure.phone:
                phone = utils.normalize_phone_number(line[7])
                if phone:
                    structure.phone = phone
                    modified = True

            if not structure.url:
                url = line[9] if line[9].lower() != "lien" else ""
                if url:
                    structure.url = url
                    modified = True

            short_desc, full_desc = utils.normalize_description(
                line[10], limit=Structure.short_desc.field.max_length
            )

            if not structure.short_desc and short_desc:
                structure.short_desc = short_desc
                modified = True
            if not structure.full_desc and full_desc:
                structure.full_desc = full_desc
                modified = True

            if modified:
                structure.log_note(
                    bot_user,
                    "Structure mise à jour par une invitation en masse",
                )
                structure.modification_date = timezone.now()
                structure.last_editor = bot_user
                structure.save()

            self.stdout.write(
                f"Structure {structure.name} ({structure.department}) traitée: {structure.get_frontend_url()}"
            )

            new_admin = line[8]
            if new_admin:
                self.invite_user(structure, new_admin)

            for service_num in range(10):
                idx_start = 14 + service_num * 8
                service_name = line[idx_start]
                if service_name:
                    self.create_service(structure, line, idx_start, bot_user)

    def invite_user(self, structure, email):
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = User.objects.create_user(
                email,
            )
        try:
            member = StructurePutativeMember.objects.get(user=user, structure=structure)
            self.stdout.write(f"    Member {member.user.email} already invited")
            if not member.is_admin:
                member.is_admin = True
                member.save()
        except StructurePutativeMember.DoesNotExist:
            try:
                member = StructureMember.objects.get(user=user, structure=structure)
                self.stdout.write(f"    Member {member.user.email} already exists")
                if not member.is_admin:
                    member.is_admin = True
                    member.save()
            except StructureMember.DoesNotExist:
                member = StructurePutativeMember.objects.create(
                    user=user,
                    structure=structure,
                    invited_by_admin=True,
                    is_admin=True,
                )
                tmp_token = Token.objects.create(
                    user=user,
                    expiration=timezone.now() + settings.INVITATION_LINK_EXPIRATION,
                )
                self.stdout.write(f"    Inviting {member.user.email}")
                send_invitation_email(
                    member,
                    "L’équipe DORA",
                    tmp_token.key,
                )

    def create_service(self, structure, line, idx_start, user):

        service = Service.objects.create(
            name=Truncator(line[idx_start]).chars(Service.name.field.max_length),
            structure=structure,
            short_desc=Truncator(line[idx_start + 1]).chars(
                Service.short_desc.field.max_length
            ),
            creator=user,
            last_editor=user,
            status=ServiceStatus.DRAFT,
            has_fee=not line[idx_start + 6].lower() == "gratuit",
            modification_date=timezone.now(),
        )
        try:
            t1 = line[idx_start + 2]
            service.kinds.add(ServiceKind.objects.get(label=t1))
        except ServiceKind.DoesNotExist:
            pass
        try:
            t2 = line[idx_start + 3]
            service.kinds.add(ServiceKind.objects.get(label=t2))
        except ServiceKind.DoesNotExist:
            pass
