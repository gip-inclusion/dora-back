# Generated by Django 3.2.12 on 2022-02-11 17:28

from django.db import migrations

from dora.admin_express.models import AdminDivisionType


def set_default_diffusion_zone(apps, schema_editor):
    Service = apps.get_model("services", "Service")
    for service in Service.objects.all():
        if service.city_code:
            diffusion_zone_details = service.city_code
        else:
            diffusion_zone_details = service.structure.city_code
        Service.objects.filter(pk=service.pk).update(
            diffusion_zone_type=AdminDivisionType.CITY,
            diffusion_zone_details=diffusion_zone_details,
        )


def noop(apps, schema_editor):
    Service = apps.get_model("services", "Service")
    Service.objects.update(diffusion_zone_details="", diffusion_zone_type="")


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0036_auto_20220211_1858"),
    ]

    operations = [
        migrations.RunPython(set_default_diffusion_zone, noop),
    ]
