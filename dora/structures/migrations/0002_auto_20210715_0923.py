# Generated by Django 3.2.5 on 2021-07-15 09:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("structures", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="structure",
            name="address",
        ),
        migrations.RemoveField(
            model_name="structure",
            name="other_themes",
        ),
        migrations.RemoveField(
            model_name="structure",
            name="solutions_kinds",
        ),
        migrations.RemoveField(
            model_name="structure",
            name="solutions_themes",
        ),
        migrations.AddField(
            model_name="structure",
            name="address1",
            field=models.CharField(default="", max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="structure",
            name="address2",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="structure",
            name="city",
            field=models.CharField(max_length=255),
        ),
    ]
