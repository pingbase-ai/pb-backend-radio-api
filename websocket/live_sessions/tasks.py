from user.models import UserSession
from events.models import Event
from user.constants import SESSION_RECORDING
from home.event_types import SUCCESS, AUTOMATIC, SESSION, SESSION_RECORDING_NAME

import logging

logger = logging.getLogger("django")


def create_session_event(storage_url, session, enduser_id, total_duration):

    try:
        logger.info(f"Creating event for session {session.session_id}")
        total_sessions = UserSession.objects.filter(
            user_id=enduser_id,
        ).count()
        Event.objects.create(
            event_type=SESSION_RECORDING,
            source_user_id=enduser_id,
            destination_user_id=None,
            status=SUCCESS,
            duration=total_duration,
            frontend_screen="NA",
            agent_name=None,
            initiated_by=AUTOMATIC,
            interaction_type=SESSION,
            interaction_id=session.session_id,
            is_parent=False,
            storage_url=storage_url,
            organization=session.user.end_user.organization,
            name=f"{SESSION_RECORDING_NAME} {total_sessions}",
        )
    except Exception as e:
        logger.error(f"Error during create_event: {e}")
