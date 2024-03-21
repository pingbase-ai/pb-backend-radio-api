from django.db.models.signals import post_save
from django.dispatch import receiver
from dyte.models import DyteMeeting, DyteAuthToken
from django.conf import settings
from user.models import EndUser


import logging

logger = logging.getLogger("django")


@receiver(post_save, sender=EndUser)
def create_dyte_meeting(sender, instance, created, **kwargs):
    """
    Signal to create a DyteMeeting instance and auth token for the endUser.
    """
    logger.info(f"create_dyte_meeting signal triggered for endUser: {instance}")
    if created:
        try:
            # Create a DyteMeeting instance for the endUser
            meeting = DyteMeeting.create_meeting(instance)

            # Create auth token for the endUser
            authToken = DyteAuthToken.create_dyte_auth_token(
                meeting, False, end_user=instance
            )
        except Exception as e:
            logger.error(f"Error while creating Dyte meeting and auth token: {e}")
