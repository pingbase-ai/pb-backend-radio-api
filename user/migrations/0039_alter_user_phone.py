# Generated by Django 4.2.10 on 2024-06-29 11:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0038_alter_client_is_client_online"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="phone",
            field=models.CharField(
                blank=True, default="", max_length=25, null=True, unique=True
            ),
        ),
    ]
