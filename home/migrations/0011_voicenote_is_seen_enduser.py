# Generated by Django 4.2.10 on 2024-03-20 17:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0010_enduserlogin_is_seen"),
    ]

    operations = [
        migrations.AddField(
            model_name="voicenote",
            name="is_seen_enduser",
            field=models.BooleanField(default=False),
        ),
    ]
