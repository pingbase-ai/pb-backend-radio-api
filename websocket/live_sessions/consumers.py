from azure.storage.blob.aio import BlobServiceClient
from channels.generic.websocket import AsyncWebsocketConsumer
from datetime import datetime
from django.conf import settings
from websocket.utils import RedisPool
from urllib.parse import parse_qs

import json
import logging
import asyncio


logger = logging.getLogger("django")


class EndUserConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            logger.info("Starting connection process")
            from user.models import UserSession

            query_string = parse_qs(self.scope["query_string"].decode())
            token = query_string.get("token", [None])[0]

            self.channel_type = self.scope["url_route"]["kwargs"]["channel_type"]
            self.org_id = token or None
            self.enduser_id = self.scope["url_route"]["kwargs"]["enduser_id"]
            self.session_id = self.scope["url_route"]["kwargs"]["session_id"]
            self.channel_group_name = (
                f"{self.channel_type}_{self.org_id}_{self.enduser_id}_{self.session_id}"
            )

            self.redis_key = f"events_{self.channel_group_name}"

            # Use the shared Redis connection pool
            self.redis = await RedisPool.get_instance()

            # Join the end user's private channel
            await self.channel_layer.group_add(
                self.channel_group_name, self.channel_name
            )

            # Accept the WebSocket connection
            await self.accept()

            # Create a new session object asynchronously without blocking
            self.session_task = asyncio.create_task(
                UserSession.objects.acreate(
                    session_id=self.session_id,
                    user_id=self.enduser_id,
                )
            )

            # Initialize a local buffer for events
            self.event_buffer = []
            self.buffer_flush_task = None

            # Initialize a list to store the first X events
            self.initial_events = []

            logger.info(
                f"Connection established successfully -- {self.channel_group_name}"
            )
        except Exception as e:
            logger.error(f"Error during connect: {e}")
            await self.close()

    async def disconnect(self, close_code):
        try:
            logger.info(f"Starting disconnection process -- {self.channel_group_name}")
            # Leave the end user's private channel
            await self.channel_layer.group_discard(
                self.channel_group_name, self.channel_name
            )

            # Ensure the session creation task has completed
            if self.session_task:
                try:
                    self.session = await asyncio.wait_for(
                        self.session_task, timeout=5.0
                    )
                except asyncio.TimeoutError:
                    logger.error("Session creation task timed out during disconnect")
                    self.session = None

            # Flush the local event buffer to Redis
            if self.event_buffer:
                await self.flush_event_buffer()

            # Push the events to azure storage
            storage_url = await asyncio.wait_for(
                self.save_events_to_azure(), timeout=10.0
            )

            if self.session:
                try:
                    if storage_url:
                        # Add this storage_url to the session object
                        self.session.storage_url = storage_url

                    await asyncio.wait_for(self.session.asave(), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.error(
                        "Saving session storage_url timed out during disconnect"
                    )
            logger.info(f"Disconnection process completed -- {self.channel_group_name}")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json["message"]

            # Add the event to the local buffer
            self.event_buffer.append(json.dumps(text_data_json))

            # Store the first X events in the initial_events list
            if len(self.initial_events) < 10:
                self.initial_events.append(text_data_json)
                await self.save_initial_events()

            # If the buffer size exceeds a threshold, flush it to Redis
            if len(self.event_buffer) >= 100:
                await self.flush_event_buffer()

            # Schedule buffer flushing task if not already scheduled
            if not self.buffer_flush_task:
                self.buffer_flush_task = asyncio.create_task(
                    self.flush_buffer_periodically()
                )

            # EndUser pushing an event to their private channel
            await self.channel_layer.group_send(
                self.channel_group_name,
                {
                    "type": "session_message",
                    "message": message,
                    "sender_channel_name": self.channel_name,
                },
            )
        except Exception as e:
            logger.error(f"Error during receive: {e}")

    async def save_initial_events(self):
        try:
            # Ensure the session creation task has completed
            if self.session_task:
                try:
                    self.session = await asyncio.wait_for(
                        self.session_task, timeout=5.0
                    )
                except asyncio.TimeoutError:
                    logger.error("Session creation task timed out during event receive")
                    return

            # Update the session object with the initial events
            if self.session:
                self.session.initial_events = self.initial_events
                await self.session.asave()
        except Exception as e:
            logger.error(f"Error during save_initial_events: {e}")

    async def flush_event_buffer(self):
        if self.event_buffer:
            await self.redis.rpush(self.redis_key, *self.event_buffer)
            self.event_buffer = []

    async def flush_buffer_periodically(self):
        try:
            while True:
                await asyncio.sleep(1)
                await self.flush_event_buffer()
        except asyncio.CancelledError:
            await self.flush_event_buffer()

    async def session_message(self, event):
        try:
            message = event["message"]
            sender_channel_name = event["sender_channel_name"]

            # Send message to WebSocket only if it is not the sender
            if self.channel_name != sender_channel_name:
                await self.send(text_data=json.dumps({"message": message}))
        except Exception as e:
            logger.error(f"Error during session_message: {e}")

    async def save_events_to_azure(self):
        try:
            connection_string = settings.AZURE_STORAGE_CONNECTION_STRING
            container_name = settings.AZURE_STORAGE_CONTAINER_NAME
            prefix = settings.AZURE_STORAGE_SESSIONS_PREFIX
            blob_name = f"{prefix}/{self.org_id}/{self.channel_group_name}/{datetime.utcnow().isoformat()}.json"

            blob_service_client = BlobServiceClient.from_connection_string(
                connection_string
            )
            blob_client = blob_service_client.get_blob_client(
                container=container_name, blob=blob_name
            )

            # Retrieve events from Redis in batches
            events = []
            while True:
                batch = await self.redis.lrange(self.redis_key, 0, 99)
                if not batch:
                    break
                events.extend([json.loads(event) for event in batch])
                await self.redis.ltrim(self.redis_key, len(batch), -1)

            if not events:
                return None
            # Convert the events list to JSON and upload
            events_json = json.dumps(events)
            try:
                await blob_client.upload_blob(events_json)
            finally:
                # Ensure that the client is properly closed
                await blob_service_client.close()
                await blob_client.close()

            # Return the blob URL
            return blob_client.url
        except Exception as e:
            logger.error(f"Error during save_events_to_azure: {e}")
            return None


class ClientConsumer(AsyncWebsocketConsumer):
    async def connect(self):

        query_string = parse_qs(self.scope["query_string"].decode())
        token = query_string.get("token", [None])[0]

        self.channel_type = self.scope["url_route"]["kwargs"]["channel_type"]
        self.org_id = token or None
        self.enduser_id = self.scope["url_route"]["kwargs"]["enduser_id"]
        self.session_id = self.scope["url_route"]["kwargs"]["session_id"]
        self.channel_group_name = (
            f"{self.channel_type}_{self.org_id}_{self.enduser_id}_{self.session_id}"
        )

        # Join the end user's private channel
        await self.channel_layer.group_add(self.channel_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        # Leave the end user's private channel
        await self.channel_layer.group_discard(
            self.channel_group_name, self.channel_name
        )

    async def session_message(self, event):
        message = event["message"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))
