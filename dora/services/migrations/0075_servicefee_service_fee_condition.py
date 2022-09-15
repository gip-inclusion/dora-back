# Generated by Django 4.0.7 on 2022-09-19 14:01

import django.db.models.deletion
from django.db import migrations, models


def add_fee_conditions(apps, schema_editor):
    ServiceFee = apps.get_model("services", "ServiceFee")
    ServiceFee.objects.create(value="gratuit", label="Gratuit")
    ServiceFee.objects.create(
        value="gratuit-sous-conditions", label="Gratuit sous conditions"
    )
    ServiceFee.objects.create(value="payant", label="Payant")
    ServiceFee.objects.create(value="adhesion", label="Adhésion")


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0074_alter_service_can_update_categories"),
    ]

    operations = [
        migrations.CreateModel(
            name="ServiceFee",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("value", models.CharField(db_index=True, max_length=255, unique=True)),
                ("label", models.CharField(max_length=255)),
            ],
            options={
                "verbose_name": "Frais à charge",
            },
        ),
        migrations.AddField(
            model_name="service",
            name="fee_condition",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="services.servicefee",
                verbose_name="Frais à charge",
            ),
        ),
        migrations.RunPython(
            add_fee_conditions, reverse_code=migrations.RunPython.noop
        ),
    ]
