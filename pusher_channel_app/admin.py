from django.contrib import admin
from .models import PusherChannelApp


# Register your models here.


@admin.register(PusherChannelApp)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "app_name",
        "app_description",
        "organization",
    )
