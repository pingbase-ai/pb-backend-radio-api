# Generated by Django 4.2.10 on 2024-03-19 09:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0007_call_is_parent_meeting_is_parent_voicenote_is_parent"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="call",
            name="scheduled_time",
        ),
        migrations.AlterField(
            model_name="call",
            name="start_time",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
    ]