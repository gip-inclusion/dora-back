# Generated by Django 4.2.10 on 2024-04-08 22:18

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0005_alter_notification_counter_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="notificationlog",
            options={"verbose_name": "historique de notification"},
        ),
        migrations.RemoveIndex(
            model_name="notificationlog",
            name="notificatio_task_ty_a4ef85_idx",
        ),
        migrations.RemoveIndex(
            model_name="notificationlog",
            name="notificatio_status_a242db_idx",
        ),
    ]
