# Generated by Django 4.2.10 on 2024-04-06 08:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0018_alter_client_organization_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="enduser",
            name="welcome_note_sent",
            field=models.BooleanField(default=False),
        ),
    ]
