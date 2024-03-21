# Generated by Django 4.2.10 on 2024-03-15 15:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0008_alter_officehours_organization"),
        ("dyte", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="dytemeeting",
            name="client",
        ),
        migrations.AddField(
            model_name="dytemeeting",
            name="end_user",
            field=models.OneToOneField(
                default=None,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="dyte_meeting",
                to="user.enduser",
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="dyteauthtoken",
            name="client",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="dyte_auth_tokens",
                to="user.client",
            ),
        ),
        migrations.AlterField(
            model_name="dyteauthtoken",
            name="end_user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="dyte_auth_tokens",
                to="user.enduser",
            ),
        ),
    ]