from pusher import Pusher
from .models import User, EndUser, Organization
from pusher_channel_app.utils import publish_event_to_user, publish_event_to_channel
from .constants import PINGBASE_BOT
from infra_utils.utils import encode_base64
from events.models import Event
from home.event_types import WE_SENT_AUDIO_NOTE, SUCCESS, AUTOMATIC, VOICE_NOTE

import uuid
import logging


logger = logging.getLogger("django")


def send_voice_note(user_id, type):
    user = User.objects.get(id=user_id)
    endUser = user.end_user
    organization = endUser.organization
    event_type = WE_SENT_AUDIO_NOTE
    if type == "welcome_note":
        if not endUser.welcome_note_sent:
            welcomeNote = organization.welcome_note
            storage_url = welcomeNote.storage_url
            play_time = welcomeNote.play_time
            title = welcomeNote.title
            description = welcomeNote.description

            unique_id = uuid.uuid4()
            try:
                # create events for the voice note
                # interaction_id should be unique here.
                event = Event.create_event_async(
                    event_type=event_type,
                    source_user_id=None,
                    destination_user_id=user.id,
                    status=SUCCESS,
                    duration=0,
                    frontend_screen="VoiceNote",
                    agent_name=None,
                    initiated_by=AUTOMATIC,
                    interaction_type=VOICE_NOTE,
                    interaction_id=unique_id,
                    is_parent=True,
                    storage_url=storage_url,
                    organization=organization,
                )
            except Exception as e:
                logger.error(f"Error while creating welcome note event: {e}")

            pusher_data_obj = {
                "source_event_type": "voice_note",
                "id": str(unique_id),
                "storage_url": storage_url,
                "sender": PINGBASE_BOT,
                "play_time": str(play_time),
                "title": title,
                "description": description,
                "event_type": "welcome_note",
            }
            try:
                publish_event_to_user(
                    organization.token,
                    "private",
                    encode_base64(f"{user.id}"),
                    "client-event",
                    pusher_data_obj,
                )
                endUser.welcome_note_sent = True
                endUser.save()
            except Exception as e:
                logger.error(f"Error while sending welcome note: {e}")

            try:
                publish_event_to_channel(
                    organization.token,
                    "private",
                    "client-event",
                    pusher_data_obj,
                )
            except Exception as e:
                logger.error(f"Error while sending welcome note to channel: {e}")

    elif type == "call_you_back_note":
        callYouBackNote = organization.call_you_back_note
        storage_url = callYouBackNote.storage_url
        play_time = callYouBackNote.play_time
        title = callYouBackNote.title
        description = callYouBackNote.description

        unique_id = uuid.uuid4()

        pusher_data_obj = {
            "source_event_type": "voice_note",
            "id": str(unique_id),
            "storage_url": storage_url,
            "sender": PINGBASE_BOT,
            "play_time": str(play_time),
            "title": title,
            "description": description,
            "event_type": "call_you_back_note",
        }

        try:
            # create a call you back note event
            event = Event.create_event_async(
                event_type=event_type,
                source_user_id=None,
                destination_user_id=user.id,
                status=SUCCESS,
                duration=0,
                frontend_screen="VoiceNote",
                agent_name=None,
                initiated_by=AUTOMATIC,
                interaction_type=VOICE_NOTE,
                interaction_id=unique_id,
                is_parent=True,
                storage_url=storage_url,
                organization=organization,
            )
        except Exception as e:
            logger.error(f"Error while creating call you back note event: {e}")
        try:
            publish_event_to_user(
                organization.token,
                "private",
                encode_base64(f"{user.id}"),
                "client-event",
                pusher_data_obj,
            )
        except Exception as e:
            logger.error(f"Error while sending call you back note: {e}")

        try:
            publish_event_to_channel(
                organization.token,
                "private",
                "client-event",
                pusher_data_obj,
            )
        except Exception as e:
            logger.error(f"Error while sending call you back note: {e}")
    elif type == "out_of_office_note":
        outOfOfficeNote = organization.out_of_office_note
        storage_url = outOfOfficeNote.storage_url
        play_time = outOfOfficeNote.play_time
        title = outOfOfficeNote.title
        description = outOfOfficeNote.description

        unique_id = uuid.uuid4()

        pusher_data_obj = {
            "source_event_type": "voice_note",
            "id": str(unique_id),
            "storage_url": storage_url,
            "sender": PINGBASE_BOT,
            "play_time": str(play_time),
            "title": title,
            "description": description,
            "event_type": "out_of_office_note",
        }

        try:
            # create an out of office note event
            event = Event.create_event_async(
                event_type=event_type,
                source_user_id=None,
                destination_user_id=user.id,
                status=SUCCESS,
                duration=0,
                frontend_screen="VoiceNote",
                agent_name=None,
                initiated_by=AUTOMATIC,
                interaction_type=VOICE_NOTE,
                interaction_id=unique_id,
                is_parent=True,
                storage_url=storage_url,
                organization=organization,
            )
        except Exception as e:
            logger.error(f"Error while creating out of office note event: {e}")
        try:
            publish_event_to_user(
                organization.token,
                "private",
                encode_base64(f"{user.id}"),
                "client-event",
                pusher_data_obj,
            )
        except Exception as e:
            logger.error(f"Error while sending out of office note: {e}")

        try:
            publish_event_to_channel(
                organization.token,
                "private",
                "client-event",
                pusher_data_obj,
            )
        except Exception as e:
            logger.error(f"Error while sending out of office note: {e}")
    else:
        logger.error(f"Invalid voice note type: {type}")
        return
