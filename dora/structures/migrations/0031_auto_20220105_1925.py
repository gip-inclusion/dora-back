# Generated by Django 3.2.11 on 2022-01-05 18:25

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("structures", "0030_rename_is_valid_structuremember_has_accepted_invitation"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="structuremember",
            name="has_accepted_invitation",
        ),
        migrations.CreateModel(
            name="StructurePutativeMember",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("will_be_admin", models.BooleanField(default=False)),
                ("creation_date", models.DateTimeField(auto_now_add=True)),
                ("invited_by_admin", models.BooleanField(default=False)),
                (
                    "structure",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="structures.structure",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Membre Potentiel",
            },
        ),
        migrations.AddConstraint(
            model_name="structureputativemember",
            constraint=models.UniqueConstraint(
                fields=("user", "structure"),
                name="structures_unique_putative_member_by_structure",
            ),
        ),
    ]
