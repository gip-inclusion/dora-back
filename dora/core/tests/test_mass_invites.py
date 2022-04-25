import csv
import tempfile
from io import StringIO

from django.core import mail
from django.core.management import call_command
from model_bakery import baker
from rest_framework.test import APITestCase

from dora.core.test_utils import make_structure
from dora.structures.models import (
    Structure,
    StructureMember,
    StructurePutativeMember,
    StructureSource,
)
from dora.users.models import User


class MassInviteTestCase(APITestCase):
    def setUp(self):
        self.tmp_file = tempfile.NamedTemporaryFile(mode="w", newline="")
        self.csv_writer = self.create_csv(self.tmp_file)

    def create_csv(self, file):
        writer = csv.writer(file, delimiter=",")
        writer.writerow(["name", "siret", "parent", "email", "is_admin"])
        return writer

    def add_row(self, row):
        self.csv_writer.writerow(row)

    def call_command(self):
        self.tmp_file.seek(0)
        out = StringIO()
        err = StringIO()
        call_command("mass_invite", self.tmp_file.name, stdout=out, stderr=err)
        self.tmp_file.seek(0)
        return out.getvalue(), err.getvalue()

    ########

    def test_wrong_siret_wont_create_anything(self):
        self.add_row(["foo", "12345678901234", "", "foo@buzz.com", "FALSE"])
        out, err = self.call_command()
        self.assertIn("Invalid siret 12345678901234 for foo", err)
        self.assertFalse(Structure.objects.filter(siret="12345").exists())
        self.assertFalse(User.objects.filter(email="foo@buzz.com").exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_siret_wont_create_anything(self):
        self.add_row(["foo", "1234", "", "foo@buzz.com", "FALSE"])
        out, err = self.call_command()
        self.assertIn("Invalid siret 1234 for foo", err)
        self.assertFalse(Structure.objects.filter(siret="12345").exists())
        self.assertFalse(User.objects.filter(email="foo@buzz.com").exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_can_invite_new_user(self):
        structure = make_structure()
        self.add_row([structure.name, structure.siret, "", "foo@buzz.com", "FALSE"])
        out, err = self.call_command()
        user = User.objects.filter(email="foo@buzz.com").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.get_full_name(), "foo@buzz.com")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "[DORA] Votre invitation sur DORA")
        self.assertIn(
            "foo@buzz.com",
            mail.outbox[0].body,
        )
        self.assertIn(
            f"L’équipe DORA vous a invité(e) à rejoindre la structure { structure.name }",
            mail.outbox[0].body,
        )

    def test_new_users_are_automatically_accepted(self):
        structure = make_structure()
        self.add_row([structure.name, structure.siret, "", "foo@buzz.com", "FALSE"])
        out, err = self.call_command()
        self.assertTrue(
            StructurePutativeMember.objects.filter(
                user__email="foo@buzz.com", invited_by_admin=True
            ).exists()
        )

    def test_idempotent(self):
        structure = make_structure()
        self.add_row([structure.name, structure.siret, "", "foo@buzz.com", "FALSE"])
        out1, err1 = self.call_command()
        out2, err2 = self.call_command()
        self.assertIn("Member foo@buzz.com already invited", out2)
        self.assertEquals(Structure.objects.filter(siret=structure.siret).count(), 1)
        self.assertEquals(User.objects.filter(email="foo@buzz.com").count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_can_invite_as_non_admin(self):
        structure = make_structure()
        self.add_row([structure.name, structure.siret, "", "foo@buzz.com", "FALSE"])
        out, err = self.call_command()
        members = StructurePutativeMember.objects.filter(
            user__email="foo@buzz.com", structure=structure
        )
        self.assertEqual(members.count(), 1)
        self.assertFalse(members[0].is_admin)

    def test_can_invite_as_admin(self):
        structure = make_structure()
        self.add_row([structure.name, structure.siret, "", "foo@buzz.com", "TRUE"])
        out, err = self.call_command()
        members = StructurePutativeMember.objects.filter(
            user__email="foo@buzz.com", structure=structure, invited_by_admin=True
        )
        self.assertEqual(members.count(), 1)
        self.assertTrue(members[0].is_admin)

    def test_admin_is_TRUE_or_FALSE(self):
        structure = make_structure()
        self.add_row([structure.name, structure.siret, "", "foo@buzz.com", "XXX"])
        out, err = self.call_command()
        self.assertIn("is_admin", err)
        self.assertIn("Must be a valid boolean", err)
        self.assertEquals(User.objects.filter(email="foo@buzz.com").count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_is_valid(self):
        structure = make_structure()
        self.add_row([structure.name, structure.siret, "", "foo.buzz.com", "FALSE"])
        out, err = self.call_command()
        self.assertIn("email", err)
        self.assertIn("Saisissez une adresse e-mail valide.", err)
        self.assertEquals(User.objects.filter(email="foo.buzz.com").count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_structure_name_is_valid(self):
        structure = make_structure()
        self.add_row(["", structure.siret, "", "foo@buzz.com", "FALSE"])
        out, err = self.call_command()
        self.assertIn("name", err)
        self.assertIn("Ce champ ne peut être vide.", err)
        self.assertEquals(User.objects.filter(email="foo@buzz.com").count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_invitee_not_a_valid_user_yet(self):
        structure = make_structure()
        self.add_row([structure.name, structure.siret, "", "foo@buzz.com", "FALSE"])
        out, err = self.call_command()
        user = User.objects.filter(email="foo@buzz.com").first()
        self.assertFalse(user.is_valid)

    def test_invitee_not_a_valid_member_yet(self):
        structure = make_structure()
        self.add_row([structure.name, structure.siret, "", "foo@buzz.com", "FALSE"])
        out, err = self.call_command()
        members = StructurePutativeMember.objects.filter(
            user__email="foo@buzz.com", structure=structure
        )
        self.assertTrue(members.exists())
        real_members = StructureMember.objects.filter(
            user__email="foo@buzz.com", structure=structure
        )
        self.assertFalse(real_members.exists())

    def test_can_invite_existing_user(self):
        structure = make_structure()
        user = baker.make(
            "users.User", first_name="foo", last_name="bar", is_valid=True
        )
        self.add_row([structure.name, structure.siret, "", user.email, "FALSE"])
        out, err = self.call_command()
        self.assertEqual(User.objects.filter(email=user.email).count(), 1)
        fresh_user = User.objects.filter(email=user.email).first()
        self.assertEqual(fresh_user.get_full_name(), user.get_full_name())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "[DORA] Votre invitation sur DORA")
        self.assertIn(
            fresh_user.get_short_name(),
            mail.outbox[0].body,
        )
        self.assertEqual(
            StructurePutativeMember.objects.filter(
                user=user, structure=structure
            ).count(),
            1,
        )

    def test_existing_user_stay_valid_user(self):
        structure = make_structure()
        user = baker.make(
            "users.User", first_name="foo", last_name="bar", is_valid=True
        )
        self.add_row([structure.name, structure.siret, "", user.email, "FALSE"])
        out, err = self.call_command()
        fresh_user = User.objects.filter(email=user.email).first()
        self.assertTrue(fresh_user.is_valid)

    def test_existing_user_stay_valid_member(self):
        structure = make_structure()
        user = baker.make(
            "users.User", first_name="foo", last_name="bar", is_valid=True
        )
        StructureMember.objects.create(
            structure=structure,
            user=user,
        )
        self.add_row([structure.name, structure.siret, "", user.email, "FALSE"])
        out, err = self.call_command()
        fresh_member = StructureMember.objects.get(user=user, structure=structure)
        self.assertFalse(fresh_member.is_admin)

    def test_member_can_be_promoted_to_admin(self):
        structure = make_structure()
        user = baker.make(
            "users.User", first_name="foo", last_name="bar", is_valid=True
        )
        StructureMember.objects.create(structure=structure, user=user, is_admin=False)
        self.add_row([structure.name, structure.siret, "", user.email, "TRUE"])
        out, err = self.call_command()
        fresh_member = StructureMember.objects.get(user=user, structure=structure)
        self.assertTrue(fresh_member.is_admin)

    def test_member_cant_be_demoted_from_admin(self):
        structure = make_structure()
        user = baker.make(
            "users.User", first_name="foo", last_name="bar", is_valid=True
        )
        StructureMember.objects.create(structure=structure, user=user, is_admin=True)
        self.add_row([structure.name, structure.siret, "", user.email, "FALSE"])
        out, err = self.call_command()
        fresh_member = StructureMember.objects.get(user=user, structure=structure)
        self.assertTrue(fresh_member.is_admin)

    def test_create_new_branch_on_the_fly(self):
        structure = make_structure(name="My Structure")
        self.add_row(["Foo", "", structure.siret, "foo@buzz.com", "FALSE"])
        out, err = self.call_command()
        branches = Structure.objects.filter(parent=structure)
        self.assertEqual(branches.count(), 1)
        branch = branches[0]
        self.assertEqual(branch.name, "Foo")
        self.assertEqual(branch.ape, structure.ape)
        self.assertEqual(branch.siret, None)
        self.assertEqual(branch.creator, User.objects.get_dora_bot())
        self.assertEqual(
            branch.source, StructureSource.objects.get(value="invitations-masse")
        )
        self.assertEqual(branch.parent, structure)

        user = User.objects.filter(email="foo@buzz.com").first()
        self.assertIsNotNone(user)
        self.assertEqual(len(mail.outbox), 1)

    def test_user_belong_to_branch(self):
        structure = make_structure(name="My Structure")
        self.add_row(["Foo", "", structure.siret, "foo@buzz.com", "FALSE"])

        out, err = self.call_command()
        branch = Structure.objects.filter(parent=structure).first()
        self.assertEqual(
            StructurePutativeMember.objects.filter(
                structure=branch, user__email="foo@buzz.com"
            ).count(),
            1,
        )
        self.assertIn(
            f"L’équipe DORA vous a invité(e) à rejoindre la structure { branch.name }",
            mail.outbox[0].body,
        )

    def test_user_dont_belong_to_parent(self):
        structure = make_structure(name="My Structure")
        self.add_row(["Foo", "", structure.siret, "foo@buzz.com", "FALSE"])

        out, err = self.call_command()
        self.assertEqual(
            StructureMember.objects.filter(
                structure=structure, user__email="foo@buzz.com"
            ).count(),
            0,
        )

    def test_find_existing_branch(self):
        structure = make_structure(name="My Structure", siret="12345678901234")
        branch = baker.make("Structure", name="Foo", siret=None, parent=structure)
        self.add_row(["Foo", "", structure.siret, "foo@buzz.com", "FALSE"])
        out, err = self.call_command()
        branches = Structure.objects.filter(parent=structure)
        self.assertEqual(branches.count(), 1)
        branch = branches[0]
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            StructurePutativeMember.objects.filter(
                structure=branch, user__email="foo@buzz.com"
            ).count(),
            1,
        )
        self.assertIn(
            f"L’équipe DORA vous a invité(e) à rejoindre la structure { branch.name }",
            mail.outbox[0].body,
        )
