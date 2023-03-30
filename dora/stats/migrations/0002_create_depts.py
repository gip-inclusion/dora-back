# Generated by Django 3.2.12 on 2022-03-17 09:39

from django.db import migrations

from dora.admin_express.models import Department


def create_depts(apps, schema_editor):
    DeploymentState = apps.get_model("stats", "DeploymentState")
    for dept in Department.objects.all():
        DeploymentState.objects.create(
            department_code=dept.code, department_name=dept.name
        )


def delete_depts(apps, schema_editor):
    DeploymentState = apps.get_model("stats", "DeploymentState")
    DeploymentState.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("stats", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_depts, reverse_code=delete_depts),
    ]
