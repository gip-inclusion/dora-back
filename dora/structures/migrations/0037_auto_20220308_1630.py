# Generated by Django 3.2.12 on 2022-03-08 15:30

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("structures", "0036_auto_20220308_1254"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="structuresource",
            options={"verbose_name": "Source"},
        ),
        migrations.AlterModelOptions(
            name="structuretypology",
            options={"verbose_name": "Typologie"},
        ),
    ]
