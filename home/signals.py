from django.db.models.signals import post_save
from django.dispatch import receiver
from home.models import Meeting, Call, VoiceNote, EndUserLogin
from django.conf import settings
from user.models import EndUser
from events.models import Event
from home.event_types import LOGGED_IN, SUCCESS, MANUAL, LOGIN, VOICE_NOTE, CALL


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
                storage_url=None,
            )
        except Exception as e:
            logger.error(f"Error while creating login event: {e}")


@receiver(post_save, sender=VoiceNote)
def create_voice_note_event(sender, instance, created, **kwargs):
    """
    Signal to create an event for voice note.
    """

    # a new voice record
    if created:
        try:
            event = Event.create_event_async(
                event_type=VOICE_NOTE,
                source_user_id=instance.sender.id,
                destination_user_id=instance.receiver.id,
                status=SUCCESS,
                duration=0,
                frontend_screen="VoiceNote",
                agent_name=None,
                initiated_by=MANUAL,
                interaction_type=VOICE_NOTE,
                interaction_id=instance.voice_note_id,
                is_parent=instance.is_parent,
                storage_url=instance.audio_file_url,
            )
        except Exception as e:
            logger.error(f"Error while creating voice note event: {e}")
    else:
        # update the existing record of event
        try:
            event = Event.objects.filter(
                interaction_type=VOICE_NOTE, interaction_id=instance.voice_note_id
            ).first()
            event.source_user_id = instance.sender.id
            event.destination_user_id = instance.receiver.id
            event.save()
        except Exception as e:
            logger.error(f"Error while updating voice note event: {e}")


# DEPRICATION WARNING: This signal is deprecated and will be removed in the future.
# @receiver(post_save, sender=Call)
# def create_call_event(sender, instance, created, **kwargs):
#     """
#     Signal to create an event for call.
#     """
#     # We don't want to create an event if the call is just schuduled
#     if not created:
#         try:
#             source_user_id = None
#             destination_user_id = None

#             if instance.caller:
#                 source_user_id = instance.caller.id
#             if instance.reciver:
#                 destination_user_id = instance.reciver.id
#             event = Event.create_event_async(
#                 event_type=instance.event_type,
#                 source_user_id=source_user_id,
#                 destination_user_id=destination_user_id,
#                 status=SUCCESS,
#                 duration=0,
#                 frontend_screen="Call",
#                 agent_name=None,
#                 initiated_by=MANUAL,
#                 interaction_type=CALL,
#                 interaction_id=instance.id,
#                 is_parent=instance.is_parent,
#             )
#         except Exception as e:
#             logger.error(f"Error while creating call event: {e}")
