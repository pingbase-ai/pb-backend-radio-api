from django.contrib import admin
from .models import DyteMeeting, DyteAuthToken


@admin.register(DyteMeeting)
class DyteAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "end_user",
    )


@admin.register(DyteAuthToken)
class DyteAuthTokenAdmin(admin.ModelAdmin):
    list_display = ("meeting", "preset")
