from pusher import Pusher
from .models import User, EndUser, Organization
from pusher_channel_app.utils import publish_event_to_user
from .constants import PINGBASE_BOT
from infra_utils.utils import encode_base64
from events.models import Event

import logging


logger = logging.getLogger("django")


def send_voice_note(user_id, type):
    user = User.objects.get(id=user_id)
    endUser = user.end_user
    organization = endUser.organization

    if type == "welcome_note":
        if not endUser.welcome_note_sent:
            welcomeNote = organization.welcome_note
            storage_url = welcomeNote.storage_url
            play_time = welcomeNote.play_time
            title = welcomeNote.title
            description = welcomeNote.description

            # create events for the voice note
            welcome_note_event = Event.create_event_async(
                "voice_note",
                None,
                user.id,
                "completed",
                play_time,
                "welcome_note",
                None,
                None,
                PINGBASE_BOT,
                None,
                None,
                None,
                True,
                storage_url,
                organization,
            )

            pusher_data_obj = {
                "source_event_type": "voice_note",
                "id": str(welcomeNote.id),
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
                    encode_base64(f"{endUser.id}"),
                    "client-event",
                    pusher_data_obj,
                )
                endUser.welcome_note_sent = True
                endUser.save()
            except Exception as e:
                logger.error(f"Error while sending welcome note: {e}")

    elif type == "call_you_back_note":
        callYouBackNote = organization.call_you_back_note
        storage_url = callYouBackNote.storage_url
        play_time = callYouBackNote.play_time
        title = callYouBackNote.title
        description = callYouBackNote.description

        pusher_data_obj = {
            "source_event_type": "voice_note",
            "id": str(callYouBackNote.id),
            "storage_url": storage_url,
            "sender": PINGBASE_BOT,
            "play_time": str(play_time),
            "title": title,
            "description": description,
            "event_type": "call_you_back_note",
        }

        # create a call you back note event
        call_you_back_note_event = Event.create_event_async(
            "voice_note",
            None,
            user.id,
            "completed",
            play_time,
            "call_you_back_note",
            None,
            None,
            PINGBASE_BOT,
            None,
            None,
            None,
            True,
            storage_url,
            organization,
        )
        try:
            publish_event_to_user(
                organization.token,
                "private",
                encode_base64(f"{endUser.id}"),
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

        pusher_data_obj = {
            "source_event_type": "voice_note",
            "id": str(outOfOfficeNote.id),
            "storage_url": storage_url,
            "sender": PINGBASE_BOT,
            "play_time": str(play_time),
            "title": title,
            "description": description,
            "event_type": "out_of_office_note",
        }

        # create an out of office note event
        out_of_office_note_event = Event.create_event_async(
            "voice_note",
            None,
            user.id,
            "completed",
            play_time,
            "out_of_office_note",
            None,
            None,
            PINGBASE_BOT,
            None,
            None,
            None,
            True,
            storage_url,
            organization,
        )
        try:
            publish_event_to_user(
                organization.token,
                "private",
                encode_base64(f"{endUser.id}"),
                "client-event",
                pusher_data_obj,
            )
        except Exception as e:
            logger.error(f"Error while sending out of office note: {e}")
    else:
        logger.error(f"Invalid voice note type: {type}")
        return
