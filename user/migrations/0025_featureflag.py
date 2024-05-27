# Generated by Django 4.2.10 on 2024-05-06 12:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0024_alter_widget_avatar"),
    ]

    operations = [
        migrations.CreateModel(
            name="FeatureFlag",
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
                ("feature_name", models.CharField(max_length=100, unique=True)),
                ("enabled", models.BooleanField(default=False)),
                (
                    "organization",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Organizations for whom the feature is enabled",
                        to="user.organization",
                    ),
                ),
            ],
        ),
    ]