import csv
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from dora.admin_express.models import City
from dora.rest_auth.models import Token
from dora.structures.emails import send_invitation_email
from dora.structures.models import Structure, StructureMember, StructureSource
from dora.users.models import User


class InviteSerializer(serializers.Serializer):
    siret = serializers.CharField(min_length=14, max_length=14)
    insee_code = serializers.CharField(max_length=5, allow_blank=True)
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    is_admin = serializers.ChoiceField(choices=("TRUE", "FALSE"))

    def validate(self, data):
        siret = data["siret"]
        try:
            structure = Structure.objects.get(siret=siret)
        except Structure.DoesNotExist:
            raise serializers.ValidationError(f"Structure {siret} doesn't exist")
        data["structure"] = structure

        city_code = data["insee_code"]
        if city_code:
            try:
                city = City.objects.get_from_code(city_code)
            except City.DoesNotExist:
                raise serializers.ValidationError(f"Invalid insee code {city_code}")
            data["city"] = city

        data["is_admin"] = True if data["is_admin"] == "TRUE" else "FALSE"
        return data


@transaction.atomic(durable=True)
class Command(BaseCommand):
    help = "Mass-send user invitations"

    def add_arguments(self, parser):
        parser.add_argument("filename")
        parser.add_argument("inviter_name")

    def handle(self, *args, **options):
        bot_user = User.objects.get_dora_bot()

        filename = options["filename"]
        inviter_name = options["inviter_name"]

        with open(filename) as invites_file:
            invites = csv.reader(invites_file, delimiter=",")
            next(invites)  # skip headers
            for i, row in enumerate(invites):
                f = InviteSerializer(
                    data={
                        "siret": row[3],
                        "insee_code": row[4],
                        "last_name": row[0][:140],
                        "first_name": row[1][:140],
                        "email": row[2],
                        "is_admin": row[5],
                    }
                )
                try:
                    f.is_valid(raise_exception=True)
                    data = f.validated_data
                    structure = data["structure"]
                    if data.get("city"):
                        structure = self.create_antenna(
                            data["structure"], data["city"], bot_user
                        )
                    self.invite_user(
                        structure,
                        data["first_name"],
                        data["last_name"],
                        data["email"],
                        data["is_admin"],
                        inviter_name,
                    )
                except serializers.ValidationError as err:
                    self.stderr.write(f"{i}: {row}")
                    self.stderr.write(str(err))

    def create_antenna(self, structure, city, bot_user):
        fake_siret = structure.siret[:9] + city.code
        try:
            antenna = Structure.objects.get(siret=fake_siret)
            assert antenna.is_antenna
        except Structure.DoesNotExist:
            self.stdout.write(f"Antenna {fake_siret} for {city.name} doesn't exist yet")

            # Create antenna on the fly, by duplicating the main structure
            # and adding the city name to its name
            antenna = Structure.objects.create(
                siret=fake_siret,
                name=f"{structure.name} – {city.name}"[:255],
                city_code=city.code,
                city=city.name,
                ape=structure.ape,
                typology=structure.typology,
                short_desc=structure.short_desc,
                full_desc=structure.full_desc,
                creator=bot_user,
                last_editor=bot_user,
                source=StructureSource.BATCH_INVITE,
                is_antenna=True,
                parent=structure,
            )
        return antenna

    def invite_user(
        self, structure, first_name, last_name, email, is_admin, inviter_name
    ):
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = User.objects.create_user(
                email,
                None,
                first_name=first_name,
                last_name=last_name,
            )
        try:
            member = StructureMember.objects.get(user=user, structure=structure)
            was_already_member = True
            self.stdout.write(f"Member {member.user.email} already exists")
        except StructureMember.DoesNotExist:
            member = StructureMember.objects.create(
                user=user, structure=structure, is_valid=False
            )
            was_already_member = False
        if is_admin is True and not member.is_admin:
            member.is_admin = True
            member.save()
        if not was_already_member:
            tmp_token = Token.objects.create(
                user=user, expiration=timezone.now() + timedelta(days=7)
            )
            self.stdout.write(f"Inviting {member.user.email}")
            send_invitation_email(
                member,
                inviter_name,
                tmp_token.key,
            )
