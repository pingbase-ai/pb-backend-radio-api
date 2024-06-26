# Generated by Django 4.2.10 on 2024-05-06 12:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0026_alter_featureflag_organization"),
    ]

    operations = [
        migrations.CreateModel(
            name="FeatureFlagConnect",
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
                        related_name="feature_flags_connect",
                        to="user.organization",
                    ),
                ),
            ],
        ),
        migrations.DeleteModel(
            name="FeatureFlag",
        ),
    ]
