from django.db import models
from infra_utils.models import CreatedModifiedModel
from user.models import Client


# Create your models here.


class CalDotCom(CreatedModifiedModel):
    cal_user_id = models.CharField(max_length=255, unique=True)
    cal_atoms_access_token = models.TextField(blank=True, null=True)
    cal_atoms_refresh_token = models.TextField(blank=True, null=True)
    client = models.OneToOneField(
        Client,
        on_delete=models.CASCADE,
        related_name="cal_dot_com",
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.cal_user_id
