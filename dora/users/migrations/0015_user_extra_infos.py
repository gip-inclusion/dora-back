# Generated by Django 4.1.3 on 2023-02-24 15:49

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0014_user_department_user_is_local_coordinator"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="onboarding_actions_accomplished",
            field=models.JSONField(default=dict),
        ),
    ]
