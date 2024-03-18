from django.conf import settings
from django_q.tasks import async_task
from rest_framework import status

from pusher_channel_app.models import (
    PusherChannelApp,
)
import threading
import logging
import pusher

logger = logging.getLogger("django")


class PusherClientSingleton:
    _instance = None
    _lock = threading.Lock()  # Adding a lock for thread-safe instance creation

    def __new__(cls):
        with cls._lock:  # Using the lock to ensure thread-safe instance creation
            if cls._instance is None:
                cls._instance = super(PusherClientSingleton, cls).__new__(cls)
                # Initialize the Pusher client only once
                cls._instance.client = pusher.Pusher(
                    app_id=settings.PUSHER_APP_ID,
                    key=settings.PUSHER_KEY,
                    secret=settings.PUSHER_SECRET,
                    cluster=settings.PUSHER_CLUSTER,
                    ssl=True,
                )
        return cls._instance

    @classmethod
    def verify_pusher_key(cls, key: str):
        return key == str(settings.PUSHER_KEY)

    @classmethod
    def get_client(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance.client

    @staticmethod
    def publish_message_async(channel, event_type, data):
        def publish_message():
            client = PusherClientSingleton.get_client()
            client.trigger(channel, event_type, {"data": data})

        task_id = async_task(publish_message)
        logger.info(f"Pusher message publish task scheduled with ID: {task_id}")


def publish_event_to_pusher(organization, data, request_meta):
    pusher_app_obj = PusherChannelApp.objects.filter(organization=organization).first()
    if not pusher_app_obj:
        logger.error("No Pusher App found for this organization")
        return {
            "error": "No Pusher App found for this organization",
            "http_status": status.HTTP_404_NOT_FOUND,
            "status": "FAILED",
        }

    pusher_client = PusherClientSingleton.get_client()

    message = data.get("message")
    channel = data.get("channel")
    event_type = data.get("event_type")
    source_user_id = data.get("source_user_id")
    destination_user_id = data.get("destination_user_id")
    status_ = data.get("status")
    frontend_screen = data.get("frontend_screen")

    try:
        pusher_client.trigger(channel, event_type, {"message": message})
        # Event.create_event(
        #     event_type=event_type,
        #     source_user_id=source_user_id,
        #     destination_user_id=destination_user_id,
        #     status=status_,
        #     frontend_screen=frontend_screen,
        #     request_meta=request_meta,
        # )
        return {"status": "success", "http_status": status.HTTP_200_OK}
    except Exception as e:
        logger.exception("Failed to publish event to Pusher")
        # Event.create_event(
        #     event_type=event_type,
        #     source_user_id=source_user_id,
        #     destination_user_id=destination_user_id,
        #     status="FAILED",
        #     frontend_screen=frontend_screen,
        #     request_meta=request_meta,
        #     error_stack_trace=str(e),
        # )
        return {
            "error": str(e),
            "http_status": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "status": "FAILED",
        }
