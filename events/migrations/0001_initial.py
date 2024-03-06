# Generated by Django 4.2.10 on 2024-02-29 09:08

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Event",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("CALL_SCHEDULED", "Call scheduled"),
                            ("SCHEDULED_CALL_HELD", "Scheduled call held"),
                            ("CALLED_US", "Called us"),
                            ("ANSWERED_OUR_CALL", "Answered our call"),
                            ("MISSED_OUR_CALL", "Missed our call"),
                            ("MISSED_THEIR_CALL", "Missed their call"),
                            ("SENT_US_AUDIO_NOTE", "Sent us audio note"),
                            ("WE_SENT_AUDIO_NOTE", "We sent audio note"),
                            ("LOGGED_IN", "Logged in"),
                            ("LEFT_WEBAPP", "Left webapp"),
                            ("DECLINED_CALL", "Declined call"),
                        ],
                        max_length=255,
                    ),
                ),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                ("source_user_id", models.IntegerField(blank=True, null=True)),
                ("destination_user_id", models.IntegerField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("IN_PROGRESS", "In progress"),
                            ("COMPLETED", "Completed"),
                            ("FAILED", "Failed"),
                        ],
                        max_length=255,
                    ),
                ),
                ("duration", models.IntegerField(blank=True, null=True)),
                ("frontend_screen", models.CharField(max_length=255)),
                ("request_meta", models.TextField()),
                ("error_stack_trace", models.TextField(blank=True, null=True)),
            ],
        ),
    ]
