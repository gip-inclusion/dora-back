import csv

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from rest_framework import serializers

from dora.rest_auth.models import Token
from dora.sirene.models import Establishment
from dora.structures.emails import send_invitation_email
from dora.structures.models import (
    Structure,
    StructureMember,
    StructurePutativeMember,
    StructureSource,
)
from dora.users.models import User

#################
# Format du CSV attendu:
#
# | name                 | siret          | parent         | email                    | is_admin |
# |----------------------|----------------|----------------|--------------------------|----------|
# | Ma structure         | 12345678901234 |                | admin1@str1.com          | TRUE     |
# | Nom de la structure1 | 12345678901234 |                | admin2@str1.com          | TRUE     |
# | Nom de la structure1 | 12345678901234 |                | user1@str1.com           | FALSE    |
# | Nom de l'antenne1    |                | 12345678901234 | admin1@ant1-str1.com     | TRUE     |
# | Mon autre structure  | 45678911234567 |                | admin1@str2.com          | TRUE     |


def structure_from_siret(siret, name, user, for_parent=False):
    try:
        structure = Structure.objects.get(siret=siret)
    except Structure.DoesNotExist:
        try:
            establishment = Establishment.objects.get(siret=siret)
        except Establishment.DoesNotExist:
            if for_parent:
                raise serializers.ValidationError(
                    f"Invalid siret {siret} for parent of {name}"
                )
            else:
                raise serializers.ValidationError(f"Invalid siret {siret} for {name}")
        structure = Structure.objects.create_from_establishment(establishment)
        structure.creator = user
        structure.last_editor = user
        structure.source = StructureSource.objects.get(value="invitations-masse")
        structure.save()
    if not for_parent and structure.name != name:
        structure.name = name
        structure.last_editor = user
        structure.save()
    return structure


def clean_siret(value):
    return "".join([c for c in value if c.isdigit()])


class InviteSerializer(serializers.Serializer):
    name = serializers.CharField()
    siret = serializers.CharField(allow_blank=True)
    parent = serializers.CharField(allow_blank=True)
    email = serializers.EmailField()
    is_admin = serializers.ChoiceField(choices=("TRUE", "FALSE"))

    def validate_is_admin(self, value):
        if value not in ["TRUE", "FALSE"]:
            raise serializers.ValidationError(
                f"is_admin should be TRUE or FALSE, not {value}"
            )
        return True if value == "TRUE" else False

    def validate(self, data):
        user = self.context["user"]
        name = data["name"]
        siret = clean_siret(data["siret"])
        parent = clean_siret(data["parent"])
        if siret and parent:
            raise serializers.ValidationError(
                f"Expecting only one of siret, parent in {name}"
            )
        if not siret and not parent:
            raise serializers.ValidationError(
                f"Expecting one of siret or parent in {name}"
            )
        if siret:
            data["structure"] = structure_from_siret(siret, name, user)
        if parent:
            data["parent_structure"] = structure_from_siret(
                parent, name, user, for_parent=True
            )
        return data


class Command(BaseCommand):
    help = "Mass-send user invitations"

    def add_arguments(self, parser):
        parser.add_argument("filename")

    def handle(self, *args, **options):
        filename = options["filename"]
        bot_user = User.objects.get_dora_bot()
        with open(filename) as invites_file:
            invites = csv.reader(invites_file, delimiter=",")
            next(invites)  # skip headers
            for i, row in enumerate(invites):
                f = InviteSerializer(
                    data={
                        "name": row[0][:255],
                        "siret": row[1],
                        "parent": row[2],
                        "email": row[3],
                        "is_admin": row[4],
                    },
                    context={"user": bot_user},
                )
                try:
                    f.is_valid(raise_exception=True)
                    data = f.validated_data
                    structure = data.get("structure")
                    if structure:
                        target_structure = structure

                    parent = data.get("parent_structure")
                    if parent:

                        branch, created = Structure.objects.get_or_create(
                            name=data["name"], parent=parent
                        )
                        if created:
                            branch.creator = bot_user
                            branch.last_editor = bot_user
                            branch.source = StructureSource.objects.get(
                                value="invitations-masse"
                            )
                            branch.save()
                        target_structure = branch

                    self.invite_user(target_structure, data["email"], data["is_admin"])

                except serializers.ValidationError as err:
                    self.stderr.write(f"{i}: {row}")
                    self.stderr.write(str(err))

    def invite_user(self, structure, email, is_admin):
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = User.objects.create_user(
                email,
            )
        try:
            member = StructurePutativeMember.objects.get(user=user, structure=structure)
            self.stdout.write(f"Member {member.user.email} already invited")
            if is_admin is True and not member.is_admin:
                member.is_admin = True
                member.save()
        except StructurePutativeMember.DoesNotExist:
            try:
                member = StructureMember.objects.get(user=user, structure=structure)
                self.stdout.write(f"Member {member.user.email} already exists")
                if is_admin is True and not member.is_admin:
                    member.is_admin = True
                    member.save()
            except StructureMember.DoesNotExist:
                member = StructurePutativeMember.objects.create(
                    user=user,
                    structure=structure,
                    invited_by_admin=True,
                    is_admin=is_admin,
                )
                tmp_token = Token.objects.create(
                    user=user,
                    expiration=timezone.now() + settings.INVITATION_LINK_EXPIRATION,
                )
                self.stdout.write(f"Inviting {member.user.email}")
                send_invitation_email(
                    member,
                    "L’équipe DORA",
                    tmp_token.key,
                )
