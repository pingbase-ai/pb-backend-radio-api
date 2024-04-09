from pusher import Pusher
from .models import User, EndUser, Organization
from pusher_channel_app.utils import publish_event_to_user
from .constants import PINGBASE_BOT
from infra_utils.utils import encode_base64

import logging


logger = logging.getLogger("django")


def send_voice_note(user_id, type):
    endUser = EndUser.objects.get(id=user_id)
    organization = endUser.organization

    if type == "welcome_note":
        if not endUser.welcome_note_sent:
            welcomeNote = organization.welcome_note
            storage_url = welcomeNote.storage_url
            play_time = welcomeNote.play_time
            title = welcomeNote.title
            description = welcomeNote.description

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