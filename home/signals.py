from django.db.models.signals import post_save
from django.dispatch import receiver
from home.models import Meeting, Call, VoiceNote, EndUserLogin
from django.conf import settings
from user.models import EndUser
from events.models import Event
from django.utils import timezone
from home.event_types import (
    LOGGED_IN,
    SUCCESS,
    MANUAL,
    LOGIN,
    VOICE_NOTE,
    CALL,
    WE_SENT_AUDIO_NOTE,
    SENT_US_AUDIO_NOTE,
)
from integrations.slack.utils import create_message_compact, Slack
from integrations.slack.models import SlackOAuth
from pusher_channel_app.utils import publish_event_to_client

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
            organization = instance.organization
            event = Event.create_event(
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
                organization=organization,
                request_meta=None,
                error_stack_trace=None,
            )

            # send pusher notification about the new login
            userObj = instance.end_user.user
            pusher_data_obj = {
                "source_event_type": "login",
                "id": str(event.id),
                "sender": f"{str(userObj.first_name)} {str(userObj.last_name)}",
                "company": f"{instance.end_user.company}",
                "timestamp": str(timezone.now()),
                "role": f"{instance.end_user.role}",
            }
            try:
                publish_event_to_client(
                    organization.token,
                    "private",
                    "enduser-event",
                    pusher_data_obj,
                )
            except Exception as e:
                logger.error(
                    f"Error while sending pusher notification for enduser login event:  {e}"
                )

        except Exception as e:
            logger.error(f"Error while creating login event: {e}")

        finally:
            # check if the last login timestamp has a diff of 1 hour
            # TODO to add slack notification when a user tab becomes active
            # send notification to slack
            org = instance.organization
            endUser = instance.end_user
            user_details = endUser.get_user_details()
            user_details_message = create_message_compact(user_details)
            message = f"User {user_details['username']} logged into the platform :technologist:  \n {user_details_message}"

            SlackOAuthObj = SlackOAuth.objects.filter(organization=org).first()
            if SlackOAuthObj and SlackOAuthObj.is_active:
                try:
                    Slack.post_message_to_slack_async(
                        access_token=SlackOAuthObj.access_token,
                        channel_id=SlackOAuthObj.channel_id,
                        message=message,
                    )
                except Exception as e:
                    logger.error(f"Error while sending slack notification: 1 {e}")
            else:
                logger.error("SlackOAuthObj not found or is inactive")


@receiver(post_save, sender=VoiceNote)
def create_voice_note_event(sender, instance, created, **kwargs):
    """
    Signal to create an event for voice note.
    """

    # a new voice record
    if created:
        try:
            organization = instance.organization
            event_type = WE_SENT_AUDIO_NOTE
            destination_user_id = None
            if not instance.is_parent:
                event_type = SENT_US_AUDIO_NOTE
            if instance.is_parent:
                destination_user_id = instance.receiver.id
            event = Event.create_event_async(
                event_type=event_type,
                source_user_id=instance.sender.id,
                destination_user_id=destination_user_id,
                status=SUCCESS,
                duration=0,
                frontend_screen="VoiceNote",
                agent_name=None,
                initiated_by=MANUAL,
                interaction_type=VOICE_NOTE,
                interaction_id=instance.voice_note_id,
                is_parent=instance.is_parent,
                storage_url=instance.audio_file_url,
                organization=organization,
            )
        except Exception as e:
            logger.error(f"Error while creating voice note event: {e}")
        finally:
            if not instance.is_parent:
                org = instance.organization
                endUser = instance.sender.end_user
                user_details = endUser.get_user_details()
                user_details_message = create_message_compact(user_details)
                message = f"User {user_details['username']} sent a voice note :notes: \n {user_details_message}"

                SlackOAuthObj = SlackOAuth.objects.filter(organization=org).first()
                if SlackOAuthObj and SlackOAuthObj.is_active:
                    try:
                        Slack.post_message_to_slack_async(
                            access_token=SlackOAuthObj.access_token,
                            channel_id=SlackOAuthObj.channel_id,
                            message=message,
                        )
                    except Exception as e:
                        logger.error(f"Error while sending slack notification: 1 {e}")
                else:
                    logger.error("SlackOAuthObj not found or is inactive")
    # else:
    #     # update the existing record of event
    #     try:
    #         event = Event.objects.filter(
    #             interaction_type=VOICE_NOTE, interaction_id=instance.voice_note_id
    #         ).first()
    #         event.source_user_id = instance.sender.id
    #         event.destination_user_id = instance.receiver.id
    #         event.save()
    #     except Exception as e:
    #         logger.error(f"Error while updating voice note event: {e}")


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


@receiver(post_save, sender=Meeting)
def create_meeting_event(sender, instance, created, **kwargs):
    """
    Signal to create an event for meeting.
    """
    if created:
        try:
            organization = instance.organization
            event = Event.create_event(
                event_type=instance.event_type,
                source_user_id=instance.organizer.id,
                destination_user_id=None,
                status=SUCCESS,
                duration=0,
                frontend_screen="Meeting",
                agent_name=None,
                initiated_by=MANUAL,
                interaction_type=instance.event_type,
                interaction_id=instance.meeting_id,
                is_parent=False,
                storage_url=None,
                organization=organization,
                request_meta=None,
                error_stack_trace=None,
            )

            userObj = instance.organizer
            pusher_data_obj = {
                "source_event_type": "scheduled_meeting",
                "id": str(event.id),
                "sender": f"{str(userObj.first_name)} {str(userObj.last_name)}",
                "company": f"{instance.organizer.end_user.company}",
                "timestamp": str(timezone.now()),
                "scheduled_time": str(instance.start_time),
                "role": f"{instance.organizer.end_user.role}",
            }
            try:
                publish_event_to_client(
                    organization.token,
                    "private",
                    "enduser-event",
                    pusher_data_obj,
                )
            except Exception as e:
                logger.error(f"Error while publishing voice note created event: {e}")

        except Exception as e:
            logger.error(f"Error while creating meeting event: {e}")
        finally:
            org = instance.organization
            endUser = instance.organizer.end_user
            user_details = endUser.get_user_details()
            user_details_message = create_message_compact(user_details)
            message = f"User {user_details['username']} scheduled a meeting :calendar: \n {user_details_message} on {instance.date}"

            SlackOAuthObj = SlackOAuth.objects.filter(organization=org).first()
            if SlackOAuthObj and SlackOAuthObj.is_active:
                try:
                    Slack.post_message_to_slack_async(
                        access_token=SlackOAuthObj.access_token,
                        channel_id=SlackOAuthObj.channel_id,
                        message=message,
                    )
                except Exception as e:
                    logger.error(f"Error while sending slack notification: 1 {e}")
            else:
                logger.error("SlackOAuthObj not found or is inactive")
    else:
        # update the existing record of event
        # TODO
        pass
