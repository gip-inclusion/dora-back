# Generated by Django 4.1.3 on 2023-03-16 15:11

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0018_alter_user_department"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="onboarding_actions_accomplished",
        ),
    ]
