# Generated by Django 4.2.10 on 2024-03-25 11:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0011_organization_slack_token"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="slack_meta",
            field=models.TextField(blank=True, null=True),
        ),
    ]
