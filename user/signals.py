from django.db.models.signals import post_save
from django.dispatch import receiver
from dyte.models import DyteMeeting, DyteAuthToken
from django.conf import settings
from user.models import EndUser, Widget
from django_q.tasks import schedule
from datetime import timedelta
from django.utils import timezone
from .utils import get_linkedIn_url
from pusher_channel_app.utils import publish_event_to_client


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


@receiver(post_save, sender=EndUser)
def send_welcome_note(sender, instance, created, **kwargs):
    if (created or not instance.welcome_note_sent) and (
        instance.organization.auto_send_welcome_note
    ):
        delay_time = int(instance.organization.auto_sent_after)
        schedule(
            "user.tasks.send_voice_note",
            instance.user.id,
            "welcome_note",
            schedule_type="O",
            next_run=timezone.now() + timedelta(seconds=delay_time),
        )


@receiver(post_save, sender=EndUser)
def fetch_linkedIn_url(sender, instance, created, **kwargs):
    if created:
        try:
            if not instance.linkedin:
                email = instance.user.email
                linkedInUrl = get_linkedIn_url(email)
                if linkedInUrl:
                    instance.linkedin = linkedInUrl
                    instance.save()
        except Exception as e:
            logger.error(f"Error while fetching LinkedIn URL: {e}")


@receiver(post_save, sender=Widget)
def widget_updated(sender, instance, created, **kwargs):
    if not created:
        try:
            pusher_data_obj = {
                "source_event_type": "widget_status_check",
            }

            publish_event_to_client(
                instance.organization.token,
                "private",
                "master-event",
                pusher_data_obj,
            )
        except Exception as e:
            logger.error(f"Error while sending notification to all widgets: {e}")
