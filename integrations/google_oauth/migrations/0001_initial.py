# Generated by Django 4.2.10 on 2024-03-27 09:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("user", "0017_alter_organization_auto_sent_after"),
    ]

    operations = [
        migrations.CreateModel(
            name="GoogleOAuth",
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
                    "deleted",
                    models.DateTimeField(db_index=True, editable=False, null=True),
                ),
                (
                    "deleted_by_cascade",
                    models.BooleanField(default=False, editable=False),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, null=True, verbose_name="Created Date"
                    ),
                ),
                (
                    "modified_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        null=True,
                        verbose_name="Modified Date",
                    ),
                ),
                ("meta", models.TextField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=False)),
                (
                    "client",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="google_oauth",
                        to="user.client",
                    ),
                ),
            ],
            options={
                "verbose_name": "Google OAuth",
                "verbose_name_plural": "Google OAuth",
                "db_table": "google_oauth",
            },
        ),
    ]
