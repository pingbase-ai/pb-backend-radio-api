from django.db import models
from infra_utils.models import CreatedModifiedModel
from user.models import Client

# Create your models here.


class OutlookOAuth(CreatedModifiedModel):
    meta = models.TextField(null=True, blank=True)
    client = models.OneToOneField(
        Client,
        on_delete=models.CASCADE,
        related_name="outlook_oauth",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=False)

    class Meta:
        db_table = "outlook_oauth"
        verbose_name = "Outlook OAuth"
        verbose_name_plural = "Outlook OAuth"

    def __str__(self):
        return f"{self.client.user.first_name}" + f"{self.is_active}"
