from django.contrib.auth.models import Group
from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import (
    User,
    Client,
    EndUser,
    Organization,
    OfficeHours,
    WelcomeNote,
    CallYouBackNote,
    OutOfOfficeNote,
    Widget,
    FeatureFlagConnect,
)

# Register your models here.

# admin.site.register(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(ModelAdmin):
    list_display = (
        "first_name",
        "email",
        "is_verified",
        "is_active",
        # "is_staff ",
    )


@admin.register(Client)
class ClientAdmin(ModelAdmin):
    list_display = ("organization", "job_title", "user", "role")


@admin.register(EndUser)
class EndUserAdmin(ModelAdmin):
    list_display = ("user", "organization", "is_trial")


@admin.register(Organization)
class OrganizationAdmin(ModelAdmin):
    list_display = ("name", "website", "team_name", "token")


@admin.register(OfficeHours)
class OfficeHoursAdmin(ModelAdmin):
    list_display = (
        "weekday",
        "organization",
    )


@admin.register(WelcomeNote)
class WelcomeNoteAdmin(ModelAdmin):
    list_display = ("title", "is_active", "play_time")


@admin.register(CallYouBackNote)
class CallYouBackNoteAdmin(ModelAdmin):
    list_display = ("title", "is_active", "play_time")


@admin.register(OutOfOfficeNote)
class OutOfOfficeNoteAdmin(ModelAdmin):
    list_display = ("title", "is_active", "play_time")


@admin.register(Widget)
class WidgetAdmin(ModelAdmin):
    list_display = ("organization", "position", "avatar")


@admin.register(FeatureFlagConnect)
class FeatureFlagAdmin(ModelAdmin):
    list_display = ("feature_name", "enabled")
