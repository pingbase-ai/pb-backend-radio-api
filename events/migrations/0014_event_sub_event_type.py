# Generated by Django 4.2.10 on 2024-06-26 11:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0013_event_name_alter_event_event_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="sub_event_type",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
