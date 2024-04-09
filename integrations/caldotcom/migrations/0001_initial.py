# Generated by Django 4.2.10 on 2024-04-03 10:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("user", "0018_alter_client_organization_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="CalDotCom",
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
                ("cal_user_id", models.CharField(max_length=255, unique=True)),
                ("cal_atoms_access_token", models.TextField(blank=True, null=True)),
                ("cal_atoms_refresh_token", models.TextField(blank=True, null=True)),
                (
                    "client",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cal_dot_com",
                        to="user.client",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]