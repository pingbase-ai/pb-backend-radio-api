# Generated by Django 4.2.10 on 2024-06-03 10:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0011_alter_event_event_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="event",
            name="interaction_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("CALL", "Call"),
                    ("VOICE_NOTE", "Voice Note"),
                    ("LOGIN", "Login"),
                    ("MEETING", "Meeting"),
                    ("not_applicable", "Not Applicable"),
                ],
                max_length=255,
                null=True,
            ),
        ),
    ]
