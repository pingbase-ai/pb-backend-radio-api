# Generated by Django 4.2.10 on 2024-03-25 14:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0012_rename_reciver_call_receiver_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="enduserlogin",
            old_name="Organization",
            new_name="organization",
        ),
    ]
