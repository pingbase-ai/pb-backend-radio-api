# Generated by Django 4.2.10 on 2024-03-25 15:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0014_enduser_city_enduser_country_enduser_linkedin"),
    ]

    operations = [
        migrations.AddField(
            model_name="officehours",
            name="timezone_offset",
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
    ]
