# Generated by Django 4.2.10 on 2024-06-28 08:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0037_user_phone_widget_color_1_widget_color_2_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="client",
            name="is_client_online",
            field=models.BooleanField(default=True),
        ),
    ]