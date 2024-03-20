# Generated by Django 4.2.10 on 2024-03-20 10:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="agent_name",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="event",
            name="initiated_by",
            field=models.CharField(
                blank=True,
                choices=[("AUTOMATIC", "Automatic"), ("MANUAL", "Manual")],
                max_length=255,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="event",
            name="interaction_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="event",
            name="interaction_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("CALL", "Call"),
                    ("VOICE_NOTE", "Voice Note"),
                    ("LOGIN", "Login"),
                    ("MEETING", "Meeting"),
                ],
                max_length=255,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="event",
            name="is_parent",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="event",
            name="request_meta",
            field=models.TextField(blank=True, null=True),
        ),
    ]
