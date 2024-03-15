from django.db import models
from user.models import Client, EndUser
from django.conf import settings
from infra_utils.utils import encode_base64
from infra_utils.models import CreatedModifiedModel


import requests
import logging


logger = logging.getLogger("django")


# Create your models here.
class DyteMeeting(CreatedModifiedModel):
    title = models.CharField(max_length=100)
    meeting_id = models.CharField(max_length=256, primary_key=True)
    client = models.OneToOneField(
        Client, on_delete=models.DO_NOTHING, related_name="dyte_meeting"
    )
    meta_info = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.title}" + f" - {self.client.organization.name}"

    @staticmethod
    def get_meeting_id(title, record_on_start=True, file_name_prefix=""):
        """
        Method to get the meeting ID.

        :param title: The title of the meeting.
        :param record_on_start: Whether to record the meeting on start.
        :param file_name_prefix: The prefix for the file name.
        :return: The meeting ID.
        """

        base_url = settings.DYTE_BASE_URL
        api_key = settings.DYTE_API_KEY
        org_id = settings.DYTE_ORG_ID

        end_point = f"{base_url}/meetings"

        encoded_token = encode_base64(f"{org_id}:{api_key}")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {encoded_token}",
        }

        data = {
            "title": title,
            "record_on_start": record_on_start,
            "recording_config": {
                "max_seconds": 86400,  # 24 hours
                "file_name_prefix": file_name_prefix,
            },
        }

        try:
            response = requests.post(end_point, json=data, headers=headers)
            logger.info(
                f"Response: {response.json()} \n Status Code: {response.status_code} \n Reason: {response.reason} \n"
            )

            data = response.json().get("data")
            meeting_id = data.get("id")

            return meeting_id, data

        except Exception as e:
            logger.error(f"Error while creating Dyte meeting: {e}")
            return None, None

    @classmethod
    def create_meeting(cls, client):
        """
        Class method to create a DyteMeeting instance.

        :param title: The title of the meeting.
        :param meeting_id: The ID of the meeting.
        :param client: The client who created the meeting.
        :return: An instance of DyteMeeting.
        """

        # check if any DyteMeeting instance exists for the client
        if cls.objects.filter(client=client).exists():
            return cls.objects.get(client=client)

        org_name = str(client.organization.name).capitalize()

        client_name = str(client.user.first_name).capitalize()

        title = f"{org_name} - {client_name}"

        logger.info(f"title: {title} \t file_name_prefix: {org_name}-{client_name}")

        meeting_id, meta_info = cls.get_meeting_id(
            title,
            record_on_start=True,
            file_name_prefix=f"{org_name}-{client_name}",
        )

        meeting = cls(
            title=title, meeting_id=meeting_id, client=client, meta_info=meta_info
        )
        meeting.save()

        return meeting


class DyteAuthToken(CreatedModifiedModel):

    GROUP_CALL_HOST = "group_call_host"
    GROUP_CALL_PARTICIPANT = "group_call_participant"

    PRESETS = (
        (GROUP_CALL_HOST, "Group Call Host"),
        (GROUP_CALL_PARTICIPANT, "Group Call Participant"),
    )

    token = models.TextField()

    meeting = models.ForeignKey(
        DyteMeeting, on_delete=models.DO_NOTHING, related_name="auth_tokens"
    )
    # if is_parent is True, then this token is the client auth token else enduser auth token
    is_parent = models.BooleanField(default=True)

    client = models.ForeignKey(
        Client, on_delete=models.DO_NOTHING, related_name="dyte_auth_tokens"
    )

    end_user = models.ForeignKey(
        EndUser,
        on_delete=models.DO_NOTHING,
        related_name="dyte_auth_tokens",
        null=True,
        blank=True,
    )

    preset = models.CharField(
        max_length=255, choices=PRESETS, default=GROUP_CALL_PARTICIPANT
    )

    def __str__(self):
        return f"{self.client.organization.name}"

    @staticmethod
    def get_auth_token(meeting_id, name, user_id, preset=GROUP_CALL_PARTICIPANT):
        """
        Class method to get the auth token.

        :param client: The client for which the token is to be generated.
        :param is_parent: Whether the token is for the parent client.
        :param preset: The preset for the token.
        :return: The auth token.
        """

        base_url = settings.DYTE_BASE_URL
        api_key = settings.DYTE_API_KEY
        org_id = settings.DYTE_ORG_ID

        end_point = f"{base_url}/meetings/{meeting_id}/participants"

        encoded_token = encode_base64(f"{org_id}:{api_key}")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {encoded_token}",
        }

        data = {
            "name": name,
            "preset_name": preset,
            "custom_participant_id": str(user_id),
        }

        try:

            response = requests.post(end_point, json=data, headers=headers)

            logger.info(
                f"Response: {response.json()} \n Status Code: {response.status_code} \n Reason: {response.reason} \n"
            )

            data = response.json().get("data")
            token = data.get("token")

            return token

        except Exception as e:
            logger.error(f"Error while creating Dyte auth token: {e}")
            return None

    @classmethod
    def create_dyte_auth_token(
        cls, meeting, is_parent, client, preset=GROUP_CALL_PARTICIPANT, end_user=None
    ):
        """
        Create a DyteAuthToken instance for the given meeting and client.

        Args:
            meeting (Meeting): The meeting object for which the token is being created.
            is_parent (bool): A flag indicating whether the client is a parent or not.
            client (Client): The client object for which the token is being created.
            preset (str, optional): The preset for the token. Defaults to GROUP_CALL_PARTICIPANT.
            end_user (User, optional): The end user associated with the token. Defaults to None.

        Returns:
            DyteAuthToken: The created DyteAuthToken instance.

        """
        # check if any DyteAuthToken instance exists for the client
        if is_parent:
            if cls.objects.filter(client=client, meeting=meeting).exists():
                return cls.objects.get(client=client, meeting=meeting)
        else:
            if cls.objects.filter(end_user=end_user, meeting=meeting).exists():
                return cls.objects.get(end_user=end_user, meeting=meeting)

        user_id = None
        name = None

        if is_parent:
            user_id = client.user.id
            name = str(client.user.first_name).capitalize()
        else:
            user_id = end_user.user.id
            name = str(end_user.user.first_name).capitalize()

        token = cls.get_auth_token(meeting.meeting_id, name, user_id, preset)

        auth_token = cls(
            token=token,
            meeting=meeting,
            client=client,
            preset=preset,
            end_user=end_user,
            is_parent=is_parent,
        )
        auth_token.save()

        return auth_token
