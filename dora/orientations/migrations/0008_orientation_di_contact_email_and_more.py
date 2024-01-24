# Generated by Django 4.2.7 on 2024-01-24 17:22

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orientations", "0007_orientation_last_reminder_email_sent"),
    ]

    operations = [
        migrations.AddField(
            model_name="orientation",
            name="di_contact_email",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="orientation",
            name="di_contact_name",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="orientation",
            name="di_contact_phone",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="orientation",
            name="di_service_id",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="orientation",
            name="di_service_name",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="orientation",
            name="di_structure_name",
            field=models.TextField(blank=True, default=""),
        ),
    ]
