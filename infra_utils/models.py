from django.db import models
from safedelete.models import SafeDeleteModel
from rest_framework.exceptions import APIException
from rest_framework import status


# Create your models here.
class CreatedModifiedModel(SafeDeleteModel):
    """
    Model abstracted for creating modified and created fields.
    """

    created_at = models.DateTimeField(
        verbose_name="Created Date", auto_now_add=True, null=True
    )
    modified_at = models.DateTimeField(
        verbose_name="Modified Date", auto_now=True, null=True, db_index=True
    )

    def save(self, **kwargs):
        """
        Overriding save
        :param keep_deleted:
        :param kwargs:
        :return:
        """
        return super(CreatedModifiedModel, self).save(**kwargs)

    class Meta:
        """
        Meta for CreatedModifiedModel
        """

        abstract = True


class CustomAPIException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "An error occurred."
    default_code = "error"

    # return the response with the custom error message
    def __init__(self, detail, code=None):
        self.detail = detail
        self.status_code = status.HTTP_400_BAD_REQUEST
        if code is not None:
            self.code = code
        else:
            self.code = "error"
        super().__init__(detail, code)
