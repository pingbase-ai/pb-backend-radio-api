# Generated by Django 4.2.10 on 2024-04-01 10:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0018_alter_client_organization_and_more"),
        ("events", "0005_event_storage_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="user.organization",
            ),
        ),
    ]
