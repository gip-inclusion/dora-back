from django.db import migrations

from dora.admin_express.utils import normalize_string_for_search


def normalize_admin_division_name(apps, _):
    Department = apps.get_model("admin_express", "Department")
    for department in Department.objects.all():
        department.normalized_name = normalize_string_for_search(
            department.normalized_name
        )
        department.save(update_fields=["normalized_name"])


class Migration(migrations.Migration):

    dependencies = [
        ("admin_express", "0005_auto_20220207_1209"),
    ]

    operations = [
        migrations.RunPython(normalize_admin_division_name, migrations.RunPython.noop)
    ]
