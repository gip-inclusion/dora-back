# Generated by Django 3.2.12 on 2022-03-08 11:54

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("structures", "0035_migrate_enums"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="structure",
            name="source",
        ),
        migrations.RemoveField(
            model_name="structure",
            name="typology",
        ),
        migrations.RenameModel(
            old_name="StructureSource2",
            new_name="StructureSource",
        ),
        migrations.RenameModel(
            old_name="StructureTypology2",
            new_name="StructureTypology",
        ),
        migrations.RenameField(
            model_name="structure",
            old_name="source2",
            new_name="source",
        ),
        migrations.RenameField(
            model_name="structure",
            old_name="typology2",
            new_name="typology",
        ),
    ]
