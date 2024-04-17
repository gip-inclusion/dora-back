from django.core.management.base import BaseCommand
from django.db import transaction

from dora.structures.models import Structure

"""
Transfère des élements d'une structure à une autre.

Uniquement les membres de la structure pour l'instant.

Dans l'immédiat, utile pour modifier "en masse" les rattachements de membres erronés.
On pourra y ajouter d'autres éléments rattachables à une structure (services, invitations ...).
"""


class TransferError(Exception):
    pass


class Command(BaseCommand):
    help = "Transfère les éléments rattachés à une structure vers une autre"

    def add_arguments(self, parser):
        parser.add_argument(
            "--wet-run",
            action="store_true",
            help="Par défaut, les actions sont listées, mais pas executées. Ce paramètre active de le traitement effectifs des actions demandées",
        )
        parser.add_argument(
            "--from",
            type=str,
            required=True,
            help="Identifiant de la structure source",
        )
        parser.add_argument(
            "--to",
            type=str,
            required=True,
            help="Identifiant de la structure de destination",
        )

    def handle(self, *args, **options):
        wet_run = options["wet_run"]
        source_pk = options["from"]
        dest_pk = options["to"]

        if source_pk == dest_pk:
            raise TransferError("Les structure source et destination sont identiques")

        try:
            source = Structure.objects.get(pk=source_pk)
        except Structure.DoesNotExist:
            self.stdout.write(self.style.ERROR("La structure source est introuvable"))
            return
        except Exception:
            self.stdout.write(
                self.style.ERROR(
                    f"L'identifiant de stucture est incorrect (UUID): {source_pk}"
                )
            )
            return

        try:
            dest = Structure.objects.get(pk=dest_pk)
        except Structure.DoesNotExist:
            self.stdout.write(
                self.style.ERROR("La structure de destination est introuvable")
            )
            return
        except Exception:
            self.stdout.write(
                self.style.ERROR(
                    f"L'identifiant de stucture est incorrect (UUID): {dest_pk}"
                )
            )
            return

        self.stdout.write(self.style.NOTICE(f"Transfert de '{source}' vers '{dest}'"))

        # transfert des membres
        if source_members := source.membership.all():
            self.stdout.write(
                f" - membres de '{source.name}' à transférer ({len(source_members)}):"
            )
            for member in source_members:
                admin = "(admin)" if member.is_admin else ""
                self.stdout.write(f"  - {member.user} {admin}")

            if wet_run:
                cnt = 0
                with transaction.atomic():
                    try:
                        for member in source_members:
                            if member.user not in dest.members.all():
                                member.structure = dest
                                member.save()
                                cnt += 1
                            else:
                                self.stdout.write(
                                    f"  > {member.user} est déjà membre de {dest} : suivant"
                                )

                    except Exception as ex:
                        self.stdout.write(
                            self.stryle.ERROR(
                                f" > impossible de transférer {member.user} : {ex}"
                            )
                        )

                self.stdout.write(
                    self.style.WARNING(f" > {cnt} membre(s) transféré(s)")
                )
            else:
                self.stdout.write(self.style.NOTICE(" DRY-RUN: aucun membre transféré"))
        else:
            self.stdout.write(
                self.style.WARNING(f" > aucun membre dans la structure '{source}'")
            )

        self.stdout.write("Traitement terminé !")
