# Generated by Django 4.2.10 on 2024-03-20 19:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0003_event_interaction_completed"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="is_seen_enduser",
            field=models.BooleanField(default=False),
        ),
    ]
