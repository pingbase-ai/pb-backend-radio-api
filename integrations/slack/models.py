from django.db import models
from infra_utils.models import CreatedModifiedModel
from user.models import Organization

# Create your models here.


class SlackOAuth(CreatedModifiedModel):
    access_token = models.TextField(null=True, blank=True)
    channel_id = models.CharField(max_length=255, null=True, blank=True)
    meta = models.TextField(null=True, blank=True)
    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="slack_oauth",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=False)

    class Meta:
        db_table = "slack_oauth"
        verbose_name = "Slack OAuth"
        verbose_name_plural = "Slack OAuth"

    def __str__(self):
        return self.access_token
