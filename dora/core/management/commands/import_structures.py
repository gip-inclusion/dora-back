import csv

from django.core.management.base import BaseCommand
from django.utils import timezone
from rest_framework import serializers

from dora.core.models import ModerationStatus
from dora.core.notify import send_moderation_notification
from dora.core.utils import normalize_description, normalize_phone_number
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

#################
# Format du CSV attendu:
# | nom | siret |departement | description | courriel_structure | telephone_structure | site_web | typologie_structure | prenom_responsable | noms_responsable | courriel_responsable | fonction_responsable | telephone_responsable | courriels_administrateurs | courriels_collaborateurs | immersion_facile | parcours_rsa | financeurs |


class TypologySerializer(serializers.ModelSerializer):
    # TODO
    class Meta:
        model = StructureTypology


class ImportSerializer(serializers.Serializer):
    name = serializers.CharField()
    siret = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    email = serializers.EmailField(allow_blank=True)
    phone = serializers.CharField(allow_blank=True)
    url = serializers.URLField(allow_blank=True)
    typology = serializers.CharField(allow_blank=True)
    admins = serializers.ListField(child=serializers.EmailField(), allow_empty=True)
    collabs = serializers.ListField(child=serializers.EmailField(), allow_empty=True)

    def validate_phone(self, value):
        return normalize_phone_number(value)

    def validate_siret(self, value):
        siret = "".join([c for c in value if c.isdigit()])
        if len(siret) != 14:
            raise serializers.ValidationError(f"Siret invalide: {value}")

        try:
            structure = Structure.objects.get(siret=siret)
            if structure.has_admin():
                administrators = structure.membership.filter(
                    is_admin=True, user__is_valid=True, user__is_active=True
                ).values_list("user__email", flat=True)
                raise serializers.ValidationError(
                    f"La structure {structure.name} ({siret}) a déjà les administrateurs suivants : {' '.join(administrators)}"
                )
        except Structure.DoesNotExist:
            if not Establishment.objects.filter(siret=siret).exists():
                raise serializers.ValidationError(f"Siret inconnu: {siret}")
        return siret


def to_string_array(str):
    clean_str = str.strip()
    if clean_str:
        return clean_str.split(",")
    return []


class Command(BaseCommand):
    help = "Importe une liste de structures"

    def add_arguments(self, parser):
        parser.add_argument("filename")

    def handle(self, *args, **options):
        filename = options["filename"]
        with open(filename) as invites_file:
            invites = csv.reader(invites_file, delimiter=",")
            next(invites)  # ignore l'en-tête
            for i, row in enumerate(invites):
                name = " ".join(row[0].split())
                self.stdout.write(
                    self.style.SUCCESS(f"{i}. Import de la structure {name}")
                )
                f = ImportSerializer(
                    data={
                        "name": name,
                        "siret": row[1],
                        "description": row[3],
                        "email": row[4],
                        "phone": row[5],
                        "url": row[6],
                        "typology": row[7],
                        "admins": to_string_array(row[13]),
                        "collabs": to_string_array(row[14]),
                    }
                )

                if f.is_valid():
                    data = f.validated_data
                    structure = self.structure_from_siret(
                        data["siret"],
                        data["name"],
                        data["description"],
                        data["phone"],
                        data["email"],
                        data["url"],
                    )
                    self.stdout.write((f"{structure.get_frontend_url()}"))
                    if data["admins"]:
                        self.invite_users(structure, data["admins"], as_admin=True)
                    if data["collabs"]:
                        self.invite_users(structure, data["collabs"], as_admin=False)
                else:
                    for field, errors in f.errors.items():
                        for error in errors:
                            self.stdout.write(
                                self.style.ERROR(f"{field}: {str(error)}")
                            )

    def invite_users(self, structure, emails, as_admin):
        for email in emails:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                user = User.objects.create_user(
                    email,
                )
            try:
                member = StructurePutativeMember.objects.get(
                    user=user, structure=structure
                )
                self.stdout.write(self.style.WARNING(f"{email} a déjà été invité·e"))
                if as_admin is True and not member.is_admin:
                    member.is_admin = True
                    member.save()
            except StructurePutativeMember.DoesNotExist:
                try:
                    member = StructureMember.objects.get(user=user, structure=structure)
                    self.stdout.write(f"{email} est déjà membre de la structure")
                    if as_admin is True and not member.is_admin:
                        member.is_admin = True
                        member.save()
                except StructureMember.DoesNotExist:
                    member = StructurePutativeMember.objects.create(
                        user=user,
                        structure=structure,
                        invited_by_admin=True,
                        is_admin=as_admin,
                    )
                    if as_admin:
                        self.stdout.write(f"{email} invité·e comme administrateur·rice")
                    else:
                        self.stdout.write(f"{email} invité·e comme collaborateur·rice")
                    send_invitation_email(
                        member,
                        "L’équipe DORA",
                    )

    def structure_from_siret(self, siret, name, description, phone, email, url):
        user = User.objects.get_dora_bot()
        try:
            structure = Structure.objects.get(siret=siret)
            modified = False
            self.stdout.write(f"La structure {structure.name} ({siret}) existe déjà")

        except Structure.DoesNotExist:
            establishment = Establishment.objects.get(siret=siret)
            structure = Structure.objects.create_from_establishment(establishment)
            self.stdout.write(f"Création de la structure {structure.name} ({siret})")
            structure.creator = user
            structure.source = StructureSource.objects.get(value="invitations-masse")
            send_moderation_notification(
                structure,
                user,
                "Structure créée à partir d'un import en masse",
                ModerationStatus.VALIDATED,
            )
            modified = True

        short_desc, full_desc = normalize_description(description, 280)
        if short_desc:
            if not structure.short_desc:
                modified = True
                structure.short_desc = short_desc
                if not structure.full_desc:
                    structure.full_desc = full_desc

        if phone and not structure.phone:
            modified = True
            structure.phone = phone

        if email and not structure.email:
            modified = True
            structure.email = email

        if url and not structure.url:
            modified = True
            structure.url = url

        if modified:
            structure.last_editor = user
            structure.modification_date = timezone.now()
            structure.save()

        return structure
