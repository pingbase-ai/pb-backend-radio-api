# Generated by Django 4.2.10 on 2024-03-22 05:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0004_event_is_seen_enduser"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="storage_url",
            field=models.URLField(blank=True, max_length=2000, null=True),
        ),
    ]
