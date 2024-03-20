from django.db import models
from user.models import Client, EndUser
from django.conf import settings
from infra_utils.utils import encode_base64
from infra_utils.models import CreatedModifiedModel
from .utils import GROUP_CALL_PARTICIPANT, GROUP_CALL_HOST


import requests
import logging


logger = logging.getLogger("django")


# Create your models here.
class DyteMeeting(CreatedModifiedModel):
    title = models.CharField(max_length=100)
    meeting_id = models.CharField(max_length=256, primary_key=True)
    end_user = models.OneToOneField(
        EndUser, on_delete=models.DO_NOTHING, related_name="dyte_meeting"
    )
    meta_info = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.title}" + f" - {self.end_user.organization.name}"

    @staticmethod
    def get_meeting_id(title, record_on_start=False, file_name_prefix=""):
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
    def create_meeting(cls, end_user):
        """
        Class method to create a DyteMeeting instance.

        :param title: The title of the meeting.
        :param meeting_id: The ID of the meeting.
        :param end_user: The end_user who created the meeting.
        :return: An instance of DyteMeeting.
        """

        # check if any DyteMeeting instance exists for the client
        if cls.objects.filter(end_user=end_user).exists():
            return cls.objects.get(end_user=end_user)

        org_name = str(end_user.organization.name).capitalize()

        end_user_name = str(end_user.user.first_name).capitalize()

        title = f"{org_name} - {end_user_name}"

        meeting_id, meta_info = cls.get_meeting_id(
            title,
            record_on_start=False,
            file_name_prefix=f"{org_name}-{end_user_name}",
        )

        meeting = cls(
            title=title, meeting_id=meeting_id, end_user=end_user, meta_info=meta_info
        )
        meeting.save()

        return meeting


class DyteAuthToken(CreatedModifiedModel):

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
        Client,
        on_delete=models.DO_NOTHING,
        related_name="dyte_auth_tokens",
        null=True,
        blank=True,
    )

    end_user = models.ForeignKey(
        EndUser,
        on_delete=models.DO_NOTHING,
        related_name="dyte_auth_tokens",
    )

    preset = models.CharField(
        max_length=255, choices=PRESETS, default=GROUP_CALL_PARTICIPANT
    )

    def __str__(self):
        return f"{self.end_user.organization.name}"

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
        cls, meeting, is_parent, end_user, preset=GROUP_CALL_PARTICIPANT, client=None
    ):
        """
        Create a DyteAuthToken instance for the given meeting and client.

        Args:
            meeting (Meeting): The meeting object for which the token is being created.
            is_parent (bool): A flag indicating whether the client is a parent or not.
            end_user (User): The end user associated with the token. Defaults to None.
            preset (str, optional): The preset for the token. Defaults to GROUP_CALL_PARTICIPANT.

            client (Client, optional): The client object for which the token is being created.

        Returns:
            DyteAuthToken: The created DyteAuthToken instance.

        """
        # check if any DyteAuthToken instance exists for the client
        if is_parent:
            if cls.objects.filter(
                client=client, meeting=meeting, is_parent=True
            ).exists():
                return cls.objects.get(client=client, meeting=meeting, is_parent=True)
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
