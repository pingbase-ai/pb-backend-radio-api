from django.db.models.signals import post_save
from django.dispatch import receiver
from home.models import Meeting, Call, VoiceNote, EndUserLogin
from django.conf import settings
from user.models import EndUser
from events.models import Event
from home.event_types import LOGGED_IN, SUCCESS, MANUAL, LOGIN


import logging

logger = logging.getLogger("django")


@receiver(post_save, sender=EndUserLogin)
def create_login_event(sender, instance, created, **kwargs):
    """
    Signal to create an event for endUser login.
    """
    logger.info(
        f"inside the signal -- instance - {instance}, created -- {created}",
    )
    if created:
        try:
            event = Event.create_event_async(
                event_type=LOGGED_IN,
                source_user_id=instance.end_user.user.id,
                destination_user_id=None,
                status=SUCCESS,
                duration=0,
                frontend_screen="Login",
                agent_name=None,
                initiated_by=MANUAL,
                interaction_type=LOGIN,
                interaction_id=instance.login_id,
                is_parent=False,
            )
        except Exception as e:
            logger.error(f"Error while creating login event: {e}")
