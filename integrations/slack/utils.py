from django_q.tasks import async_task
from slack_sdk import WebClient
import logging

logger = logging.getLogger("django")


class Slack:
    @staticmethod
    def post_message_to_slack_async(
        access_token: str, channel_id: str, message
    ) -> None:
        task_id = async_task(
            "integrations.slack.utils.post_message_to_slack",
            access_token,
            channel_id,
            message,
        )
        logger.info(f"Slack notify task is scheduled with task ID: {task_id}")


def post_message_to_slack(access_token: str, channel_id: str, message) -> None:
    # Create a client instance
    try:
        client = WebClient(token=access_token)
        # Post a message to the specified Slack channel
        response = client.chat_postMessage(channel=channel_id, text=message)
        logger.info(f"response: {response}")
        return response
    except Exception as e:
        logger.error(f"Error while posting message to Slack: {e}")
        return None
