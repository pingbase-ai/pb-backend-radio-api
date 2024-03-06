from pusher_channel_app.models import PusherChannelApp
from rest_framework import status
from django.conf import settings
from django_q.tasks import async_task

import pusher
import logging

logger = logging.getLogger("django")


class PusherClientSingleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PusherClientSingleton, cls).__new__(cls)
            # Initialize the pusher client with settings
            cls._instance.client = pusher.Pusher(
                app_id=settings.PUSHER_APP_ID,
                key=settings.PUSHER_KEY,
                secret=settings.PUSHER_SECRET,
                cluster=settings.PUSHER_CLUSTER,
                ssl=True,
            )
        return cls._instance

    @classmethod
    def get_client(cls):
        return cls().__class__._instance.client

    @staticmethod
    def publish_message_async(channel, event_type, data):
        # Define the function to publish a message
        def publish_message():
            client = PusherClientSingleton.get_client()
            client.trigger(channel, event_type, {"data": data})

        # Use async_task to run the publish_message function asynchronously
        task_id = async_task(publish_message)
        logger.info(f"Pusher message publish task scheduled with ID: {task_id}")


def publish_event_to_pusher(organization, data, request_meta):
    pusher_app_obj = PusherChannelApp.objects.filter(organization=organization).first()
    if not pusher_app_obj:
        return {
            "error": "No Pusher App found for this organization",
            "http_status": status.HTTP_404_NOT_FOUND,
            "status": "FAILED",
        }

    pusher_client = PusherClientSingleton().get_client()

    message = data["message"]
    channel = data["channel"]
    event_type = data["event_type"]
    source_user_id = data["source_user_id"]
    destination_user_id = data["destination_user_id"]
    status_ = data["status"]
    frontend_screen = data["frontend_screen"]

    try:
        pusher_client.trigger(channel, event_type, {"message": f"{message}"})
        Event.create_event(
            event_type=event_type,
            source_user_id=source_user_id,
            destination_user_id=destination_user_id,
            status=status_,
            duration=None,  # Consider making this parameterized as well
            frontend_screen=frontend_screen,
            request_meta=request_meta,
            error_stack_trace=None,
        )
        return {"status": "success", "http_status": status.HTTP_200_OK}
    except Exception as e:
        Event.create_event(
            event_type=event_type,
            source_user_id=source_user_id,
            destination_user_id=destination_user_id,
            status="FAILED",
            duration=None,
            frontend_screen=frontend_screen,
            request_meta=request_meta,
            error_stack_trace=str(e),
        )
        return {
            "error": str(e),
            "http_status": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "status": "FAILED",
        }
