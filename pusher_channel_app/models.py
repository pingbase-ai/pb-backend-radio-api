from django.db import models
from infra_utils.models import CreatedModifiedModel
from user.models import Organization


class PusherChannelApp(CreatedModifiedModel):
    app_id = models.CharField(max_length=255)
    key = models.CharField(max_length=255)
    secret = models.CharField(max_length=255)
    cluster = models.CharField(max_length=255)
    SSL = models.BooleanField(default=True)
    app_name = models.CharField(max_length=255)
    app_description = models.TextField(null=True, blank=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.DO_NOTHING,
        related_name="pusher_channel_apps",
        null=True,
        blank=True,
    )

    def __str__(self):
        if self.organization is None:
            return self.app_name
        else:
            return self.app_name + " - " + self.organization.name
