from django.shortcuts import render
from rest_framework.views import APIView
from infra_utils.views import CustomAPIView, CustomGenericAPIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.views.decorators.csrf import csrf_exempt
from django_q.tasks import async_task
from django.utils import timezone
from .serializers import (
    MeetingSerializer,
    CallSerializer,
    VoiceNoteSerializer,
    EndUserLoginSerializer,
)
from .models import Meeting, Call, VoiceNote, EndUserLogin, EndUserSession
from user.models import Client, User, EndUser
from .utils import upload_to_azure_blob, fetch_session_id_from_dyte
from user.utils import is_request_within_office_hours
from django.db.models import (
    Q,
    Case,
    When,
    Count,
    IntegerField,
    Prefetch,
    OuterRef,
    Subquery,
    Max,
)
from rest_framework.parsers import FileUploadParser
from .event_types import (
    CALL_SCHEDULED,
    WE_SENT_AUDIO_NOTE,
    SENT_US_AUDIO_NOTE,
    ANSWERED_OUR_CALL,
    MISSED_OUR_CALL,
    MANUAL,
    CALL,
    SUCCESS,
    CALLED_US,
    MISSED_THEIR_CALL,
    DECLINED_CALL,
)
from pusher_channel_app.utils import (
    publish_event_to_client,
    publish_event_to_user,
    publish_event_to_channel,
)
from infra_utils.utils import encode_base64, UUIDEncoder
from dyte.models import DyteMeeting, DyteAuthToken
from events.models import Event
from user.serializers import CustomEndUserSerializer
from .utils import convert_to_date, convert_webm_to_mp3

import logging
import datetime
import uuid
import json
import ffmpeg
import os

logger = logging.getLogger("django")


# Create your views here.


class ChecklistClientAPIView(CustomAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        # profile photo, voice note, call a user
        photo = bool(user.photo)
        voice_note = VoiceNote.objects.filter(sender=user, is_parent=True).exists()
        call = Call.objects.filter(caller=user, is_parent=True).exists()

        return Response({"photo": photo, "voice_note": voice_note, "call": call})


class TasksClientAPIView(CustomAPIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):

        user = request.user

        try:
            client = Client.objects.get(user=user)
        except Client.DoesNotExist:
            return Response(
                {"message": "Client not found for the user"},
                status=status.HTTP_404_NOT_FOUND,
            )

        current_time = timezone.now()
        organization = client.organization
        # Retrieve Meeting, Call, and Voice Notes data for the client
        events_stats = Event.objects.filter(organization=organization).aggregate(
            meetings=Count(
                "id",
                filter=Q(event_type="CALL_SCHEDULED", scheduled_time__gte=current_time),
            ),
            calls=Count("id", filter=Q(event_type="MISSED_THEIR_CALL", is_unread=True)),
            voice_notes=Count(
                "id", filter=Q(event_type="SENT_US_AUDIO_NOTE", is_unread=True)
            ),
        )
        return Response(events_stats)


class ActivitiesClientAPIView(CustomAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, tab, *args, **kwargs):

        user = request.user

        client = Client.objects.filter(user=user).first()

        if not client:
            return Response(
                {"message": "Client not found for the user"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        organization = client.organization

        if tab == "all":
            all_meetings = Meeting.objects.filter(
                organization=organization,
            )
            all_calls = Call.objects.filter(organization=organization)
            all_voice_notes = VoiceNote.objects.filter(organization=organization)
            all_logins = EndUserLogin.objects.filter(organization=organization)
            meetings_serializer = MeetingSerializer(all_meetings, many=True)
            calls_serializer = CallSerializer(all_calls, many=True)
            voice_notes_serializer = VoiceNoteSerializer(all_voice_notes, many=True)
            logins_serializer = EndUserLoginSerializer(all_logins, many=True)
            return Response(
                {
                    "meetings": meetings_serializer.data,
                    "calls": calls_serializer.data,
                    "voice_notes": voice_notes_serializer.data,
                    "logins": logins_serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        elif tab == "voice_notes":
            all_voice_notes = VoiceNote.objects.filter(organization=organization)
            serializer = VoiceNoteSerializer(all_voice_notes, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif tab == "scheduled_calls":
            applied_filters = request.query_params.getlist("user_ids", None)
            if applied_filters:
                scheduled_calls = Meeting.objects.filter(
                    organization=organization, attendees=user, status="scheduled"
                )
            else:
                scheduled_calls = Meeting.objects.filter(
                    organization=organization, status="scheduled"
                )
            serializer = MeetingSerializer(scheduled_calls, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif tab == "missed_calls":
            missed_calls = Call.objects.filter(organization=organization, is_seen=False)
            serializer = CallSerializer(missed_calls, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif tab == "calls":
            all_calls = Call.objects.filter(organization=organization)
            serializer = CallSerializer(all_calls, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif tab == "logins":
            all_logins = EndUserLogin.objects.filter(organization=organization)
            serializer = EndUserLoginSerializer(all_logins, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"message": "Invalid tab"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ActivitiesCreateModifyClientAPIView(CustomAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        tab = request.data.get("tab", None)

        if not tab:
            return Response(
                {"message": "Tab not provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        client = Client.objects.filter(user=user).first()
        if not client:
            return Response(
                {"message": "Client not found for the user"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        organization = client.organization
        if tab == "voice_notes":
            data = request.data
            file = request.data.get("file")
            data["organization"] = organization.id
            serializer = VoiceNoteSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        elif tab == "calls":
            data = request.data
            data["organization"] = organization.id
            serializer = CallSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(
                {"message": "Invalid tab"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def put(self, request, *args, **kwargs):
        user = request.user
        tab = request.data.get("tab", None)
        if not tab:
            return Response(
                {"message": "Tab not provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        client = Client.objects.filter(user=user).first()
        if not client:
            return Response(
                {"message": "Client not found for the user"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        organization = client.organization
        if tab == "voice_notes":
            voice_note_id = request.data.get("voice_note_id", None)
            if not voice_note_id:
                return Response(
                    {"message": "Voice note id not provided"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            voice_note = VoiceNote.objects.filter(
                voice_note_id=voice_note_id, organization=organization
            ).first()
            if not voice_note:
                return Response(
                    {"message": "Voice note not found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            voice_note.mark_as_seen(user)
            return Response(
                {"message": "Voice note marked as seen"},
                status=status.HTTP_200_OK,
            )
        elif tab == "scheduled_calls":
            meeting_id = rrequest.data.get("meeting_id", None)
            if not meeting_id:
                return Response(
                    {"message": "Meeting id not provided"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            meeting = Meeting.objects.filter(
                meeting_id=meeting_id, organization=organization
            ).first()
            if not meeting:
                return Response(
                    {"message": "Meeting not found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            status = request.data.get("status", None)
            meeting.status = status
            meeting.save()
        elif tab == "calls":
            call_id = request.data.get("call_id", None)
            if not call_id:
                return Response(
                    {"message": "Call id not provided"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            call = Call.objects.filter(
                call_id=call_id, organization=organization
            ).first()
            if not call:
                return Response(
                    {"message": "Call not found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            call.mark_as_seen(user)
            return Response(
                {"message": "Call marked as seen"},
                status=status.HTTP_200_OK,
            )


class ActivitiesEndUserAPIView(CustomAPIView):
    def get(self, request, *args, **kwargs):

        user_id = request.query_params.get("user_id", None)
        organization_id = request.query_params.get("organization_id", None)
        if not user_id or not organization_id:
            return Response(
                {"message": "Bad data"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = User.objects.filter(id=user_id).first()

        organization = Organization.objects.filter(id=organization_id).first()

        if not user or not organization:
            return Response(
                {"message": "User or organization not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        all_meetings = Meeting.objects.filter(
            attendees=user, organization=organization, status="scheduled"
        )
        all_calls = Call.objects.filter(
            Q(caller=user) | Q(receiver=user), organization=organization
        )
        all_voice_notes = VoiceNote.objects.filter(
            Q(sender=user) | Q(receiver=user), organization=organization
        )
        meetings_serializer = MeetingSerializer(all_meetings, many=True)
        calls_serializer = CallSerializer(all_calls, many=True)
        voice_notes_serializer = VoiceNoteSerializer(all_voice_notes, many=True)

        return Response(
            {
                "meetings": meetings_serializer.data,
                "calls": calls_serializer.data,
                "voice_notes": voice_notes_serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class ActivitiesCreateModifyEndUserAPIView(CustomAPIView):
    def post(self, request, *args, **kwargs):
        user_id = request.data.get("user_id", None)
        organization_id = request.data.get("organization_id", None)
        type = request.data.get("type", None)
        if not user_id or not organization_id or not type:
            return Response(
                {"message": "Bad data"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = User.objects.filter(id=user_id).first()
        organization = Organization.objects.filter(id=organization_id).first()
        if not user or not organization:
            return Response(
                {"message": "User or organization not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if type == "voice_notes":
            data = request.data
            data["organization"] = organization.id
            serializer = VoiceNoteSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        elif type == "calls":
            data = request.data
            data["organization"] = organization.id
            serializer = CallSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        elif type == "scheduled_calls":
            data = request.data
            data["organization"] = organization.id
            serializer = MeetingSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        elif type == "logged_in":
            data = request.data
            data["organization"] = organization.id

            user.is_online = True
            user.last_login = datetime.datetime.now()
            user.save()

            serializer = EndUserLoginSerializer(data=data)

            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        elif type == "logged_out":
            user.is_online = False
            user.save()
        else:
            return Response(
                {"message": "Invalid tab"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ActivitiesCreateVoiceNoteClientAPIView(CustomGenericAPIView):
    permission_classes = (IsAuthenticated,)
    # parser_classes = (FileUploadParser,)

    def post(self, request, filename, *args, **kwargs):
        user = request.user

        endUserId = request.query_params.get("endUserId")
        #
        # endUserObj = EndUser.objects.filter(id=endUserId).first()

        sender = user
        receiver = User.objects.filter(id=endUserId).first()
        if not receiver:
            return Response(
                {"message": "End user not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        file = request.FILES.get("file")
        if not file:
            return Response(
                {"message": "File not provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        audio_file_url = upload_to_azure_blob(
            file,
            f"voice-notes/{user.client.organization.name}",
            f"voice_note_{uuid.uuid4()}.mp3",
        )
        logger.info(f"\n\n\n {audio_file_url} \n\n\n")

        try:
            voice_note = VoiceNote.create_voice_note(
                sender=sender,
                receiver=receiver,
                audio_file_url=audio_file_url,
                is_parent=True,
                description=request.data.get("description", ""),
                organization=user.client.organization,
                event_type=WE_SENT_AUDIO_NOTE,
            )
            voice_note.mark_as_seen(user)

            pusher_data_obj = {
                "source_event_type": "voice_note",
                "id": str(voice_note.voice_note_id),
                "storage_url": audio_file_url,
                "sender": sender.first_name,
            }
            try:
                publish_event_to_user(
                    user.client.organization.token,
                    "private",
                    encode_base64(f"{endUserId}"),
                    "client-event",
                    pusher_data_obj,
                )
            except Exception as e:
                logger.error(f"Error while publishing voice note created event: {e}")

            try:
                publish_event_to_channel(
                    user.client.organization.token,
                    "private",
                    "client-event",
                    pusher_data_obj,
                )
            except Exception as e:
                logger.error(
                    f"Error while publishing voice note created event to channel: {e}"
                )
        except Exception as e:
            logger.error(f"Error while creating voice note: {e}")
            return Response(
                {"message": "Error while creating voice note"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"message": "Voice note created"},
            status=status.HTTP_201_CREATED,
        )


class ActivitiesViewModifyVoiceNoteClientAPIView(CustomGenericAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):

        user = request.user
        voice_note_id = request.query_params.get("voice_note_id", None)

        organization = user.client.organization

        try:
            if voice_note_id:
                voice_notes = VoiceNote.objects.filter(
                    organization=organization, voice_note_id=voice_note_id
                )
                serialized_data = VoiceNoteSerializer(voice_notes, many=True)
                return Response(serialized_data.data, status=status.HTTP_200_OK)
            voice_notes = VoiceNote.objects.filter(organization=organization)
            serialized_data = VoiceNoteSerializer(voice_notes, many=True)
            return Response(serialized_data.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error while getting voice notes: {e}")
            return Response(
                {"message": "Error while getting voice notes"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        voice_notes = VoiceNote.objects.filter(organization=organization)

    def put(self, request, *args, **kwargs):
        user = request.user
        voice_note_id = request.data.get("voice_note_id", None)
        if not voice_note_id:
            return Response(
                {"message": "Voice note id not provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        voice_note = VoiceNote.objects.filter(voice_note_id=voice_note_id).first()
        if not voice_note:
            return Response(
                {"message": "Voice note not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        voice_note.mark_as_seen(user)
        return Response(
            {"message": "Voice note marked as seen"},
            status=status.HTTP_200_OK,
        )


class ActivitiesCreateVoiceNoteEndUserAPIView(CustomGenericAPIView):
    # parser_classes = (FileUploadParser,)
    permission_classes = (AllowAny,)

    def post(self, request, filename, *args, **kwargs):

        endUserId = request.query_params.get("endUserId")
        user = User.objects.filter(id=endUserId).first()
        if not user:
            return Response(
                {"message": "End user not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        sender = user
        receiver = None
        file = request.FILES.get("file")
        if not file:
            return Response(
                {"message": "File not provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        output_filename = f"{uuid.uuid4()}.mp3"
        try:
            output_filename = convert_webm_to_mp3(file, output_filename)
        except Exception as e:
            logger.error(f"Error while converting file: {e}")
            return Response(
                {"message": "Failed to convert file:"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            audio_file_url = upload_to_azure_blob(
                open(output_filename, "rb"),
                f"voice-notes/{user.end_user.organization.name}",
                f"voice_note_{uuid.uuid4()}.mp3",
            )
            logger.info(f"\n\n\n {audio_file_url} \n\n\n")
        except Exception as e:
            logger.error(f"Error while uploading file: {e}")
            return Response(
                {"message": "Failed to upload file:"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            os.remove(output_filename)
        except Exception as e:
            logger.error(f"Error while deleting file: {e}")
            return Response(
                {"message": "Failed to delete file:"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            voice_note = VoiceNote.create_voice_note(
                sender=sender,
                receiver=receiver,
                audio_file_url=audio_file_url,
                is_parent=False,
                description=request.data.get("description", ""),
                organization=user.end_user.organization,
                event_type=SENT_US_AUDIO_NOTE,
            )
            pusher_data_obj = {
                "source_event_type": "voice_note",
                "id": str(voice_note.voice_note_id),
                "storage_url": audio_file_url,
                "sender": f"{sender.first_name} {sender.last_name}",
                "company": f"{sender.end_user.company}",
                "timestamp": str(voice_note.created_at),
                "unique_id": f"{sender.id}",
                "role": f"{sender.end_user.role}",
            }
            try:
                publish_event_to_client(
                    sender.end_user.organization.token,
                    "private",
                    "enduser-event",
                    pusher_data_obj,
                )
            except Exception as e:
                logger.error(f"Error while publishing voice note created event: {e}")
            # voice_note.mark_as_seen(user)
            return Response(
                {"message": "Voice note created"},
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.error(f"Error while creating voice note: {e}")
            return Response(
                {"message": "Error while creating voice note"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ActivitiesViewVoiceNoteEndUserAPIView(CustomGenericAPIView):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):

        endUserId = request.query_params.get("endUserId", None)

        if not endUserId:
            return Response(
                {"message": "End user id not provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(id=endUserId).first()

        endUser = user.end_user

        voiceNoteId = request.query_params.get("voiceNoteId", None)

        organization = endUser.organization

        try:
            if voiceNoteId:
                voice_notes = VoiceNote.objects.filter(
                    organization=organization, voice_note_id=voiceNoteId
                )
                serialized_data = VoiceNoteSerializer(voice_notes, many=True)
                return Response(serialized_data.data, status=status.HTTP_200_OK)
            voice_notes = VoiceNote.objects.filter(organization=organization)
            serialized_data = VoiceNoteSerializer(voice_notes, many=True)
            return Response(serialized_data.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error while getting voice notes: {e}")
            return Response(
                {"message": "Error while getting voice notes"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def post(self, request, *args, **kwargs):
        voice_note_id = request.data.get("voice_note_id", None)
        if not voice_note_id:
            return Response(
                {"message": "Voice note id not provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        voice_note = VoiceNote.objects.filter(voice_note_id=voice_note_id).first()
        if not voice_note:
            return Response(
                {"message": "Voice note not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            voice_note.is_seen_enduser = True
            voice_note.save()

            # Update the event object
            event = Event.objects.filter(
                interaction_type=VOICE_NOTE, interaction_id=voice_note_id
            ).first()
            event.interaction_completed = True
            event.save()

        except Exception as e:
            logger.error(f"Error while marking voice note as seen: {e}")
            return Response(
                {"message": "Error while marking voice note as seen"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"message": "Voice note marked as seen"},
            status=status.HTTP_200_OK,
        )


class ActivitiesCreateViewModifyCallEndUserAPIView(CustomGenericAPIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        endUserId = request.query_params.get("endUserId")
        user = request.user

        receiver = User.objects.filter(id=endUserId).first()

        endUser = receiver.end_user
        caller = user
        client = user.client
        organization = client.organization
        event_type = CALL_SCHEDULED
        is_parent = True
        try:

            call = Call.create_scheduled_call(
                receiver=receiver,
                caller=caller,
                event_type=event_type,
                is_parent=is_parent,
                organization=organization,
            )

            # Now, get the auth token for client and send it to frontend.
            endUserMeetingObj = DyteMeeting.objects.filter(end_user=endUser).first()
            if not endUserMeetingObj:
                endUserMeetingObj = DyteMeeting.create_meeting(endUser)

            endUserMeetingId = endUserMeetingObj.meeting_id

            # check if the client auth token already exists
            clientAuthToken = DyteAuthToken.objects.filter(
                meeting=endUserMeetingObj, is_parent=True, client=client
            ).first()

            if not clientAuthToken:
                # remove the existing cache from dyte
                # try:
                #     DyteAuthToken.delete_dyte_auth_token(user.id, endUserMeetingId)
                # except Exception as e:
                #     logger.error(f"Error while deleting Dyte auth token: {e}")
                clientAuthToken = DyteAuthToken.create_dyte_auth_token(
                    meeting=endUserMeetingObj,
                    is_parent=True,
                    end_user=endUser,
                    client=client,
                )

            # publish the event to the enduser
            pusher_data_obj = {
                "source_event_type": "call",
                "id": str(call.call_id),
                "meeting_id": endUserMeetingId,
                "sender": user.first_name,
                "storage_url": "",
                "photo": user.photo,
                "sender_id": user.id,
            }
            try:
                publish_event_to_user(
                    str(organization.token),
                    "private",
                    encode_base64(f"{endUserId}"),
                    "client-event",
                    pusher_data_obj,
                )
            except Exception as e:
                logger.error(f"Error while publishing call scheduled event: {e}")

            try:
                publish_event_to_channel(
                    str(organization.token),
                    "private",
                    "client-event",
                    pusher_data_obj,
                )
            except Exception as e:
                logger.error(
                    f"Error while publishing call scheduled event to channel: {e}"
                )
            return Response(
                {
                    "message": "Call scheduled",
                    "meeting_id": endUserMeetingId,
                    "auth_token": clientAuthToken.token,
                    "call_id": call.call_id,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.error(f"Error while scheduling call: {e}")
            return Response(
                {"message": "Error while scheduling call"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def get(self, request, *args, **kwargs):
        endUserId = request.query_params.get("endUserId")
        user = request.user
        client = user.client

        endUser = User.objects.filter(id=endUserId).first().end_user

        organization = endUser.organization

        try:
            all_calls = Call.objects.filter(
                Q(caller=client)
                | Q(receiver=endUser)
                | Q(caller=endUser)
                | Q(reciver=client),
                organization=organization,
            )
            serialized_data = CallSerializer(all_calls, many=True)
            return Response(serialized_data.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error while getting calls: {e}")
            return Response(
                {"message": "Error while getting calls"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def put(self, request, *args, **kwargs):
        user = request.user
        call_id = request.data.get("call_id", None)
        update_type = request.data.get("update_type", None)

        if not call_id or not update_type:
            return Response(
                {"message": "call_id or update_type not provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        call = Call.objects.filter(call_id=call_id).first()
        if not call:
            return Response(
                {"message": "Call not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            if update_type == "mark_as_seen":
                call.mark_as_seen(user)
            elif update_type == "call_accepted":
                call.event_type = ANSWERED_OUR_CALL
                # fetch the session_id from dyte for this call object
                session_id = fetch_session_id_from_dyte(
                    call.receiver.end_user.dyte_meeting.meeting_id
                )
                call.session_id = session_id
                call.save()
                # Create a new event type for this update
                agent_name = None
                if call.is_parent:
                    agent_name = call.caller.first_name
                else:
                    agent_name = call.receiver.first_name if call.receiver else None

                try:
                    organization = call.organization
                    existingEvent = Event.objects.filter(
                        interaction_id=call.call_id
                    ).first()
                    if not existingEvent:
                        event = Event.create_event_async(
                            event_type=ANSWERED_OUR_CALL,
                            source_user_id=call.caller.id,
                            destination_user_id=call.receiver.id,
                            status=SUCCESS,
                            duration=0,
                            frontend_screen="NA",
                            agent_name=agent_name,
                            initiated_by=MANUAL,
                            interaction_type=CALL,
                            interaction_id=call.call_id,
                            is_parent=call.is_parent,
                            storage_url=call.file_url,
                            organization=organization,
                        )
                except Exception as e:
                    logger.error(f"Error while creating call event: {e}")

            elif update_type == "we_accepted_the_call":
                call.event_type = CALLED_US
                session_id = fetch_session_id_from_dyte(
                    call.caller.end_user.dyte_meeting.meeting_id
                )
                call.session_id = session_id
                call.save()
                # Create a new event type for this update

                agent_name = None
                if call.is_parent:
                    agent_name = call.caller.first_name
                else:
                    agent_name = call.receiver.first_name if call.receiver else None

                try:
                    organization = call.organization
                    existingEvent = Event.objects.filter(
                        interaction_id=call.call_id
                    ).first()
                    if not existingEvent:
                        event = Event.create_event_async(
                            event_type=CALLED_US,
                            source_user_id=call.caller.id,
                            destination_user_id=call.receiver.id,
                            status=SUCCESS,
                            duration=0,
                            frontend_screen="NA",
                            agent_name=agent_name,
                            initiated_by=MANUAL,
                            interaction_type=CALL,
                            interaction_id=call.call_id,
                            is_parent=call.is_parent,
                            storage_url=call.file_url,
                            organization=organization,
                        )
                except Exception as e:
                    logger.error(f"Error while creating call event: {e}")

                # Send pusher notification to the clients that call is accepted
                try:
                    pusher_data_obj = {
                        "source_event_type": "call_accepted",
                        "id": str(call.call_id),
                        "meeting_id": call.caller.end_user.dyte_meeting.meeting_id,
                        "storage_url": "",
                        "sender": f"{call.caller.first_name} {call.caller.last_name}",
                        "company": f"{call.caller.end_user.company}",
                        "timestamp": str(call.created_at),
                        "unique_id": f"{call.caller.id}",
                        "role": f"{call.caller.end_user.role}",
                    }
                    publish_event_to_client(
                        str(organization.token),
                        "private",
                        "enduser-event",
                        pusher_data_obj,
                    )
                except Exception as e:
                    logger.error(f"Error while publishing call scheduled event: {e}")

            elif update_type == "mark_as_completed":
                call.status = "completed"
                call.save()
            elif update_type == "mark_as_missed":
                call.status = "missed"
                call.event_type = MISSED_OUR_CALL
                call.save()
                # Create a new event type for this update

                agent_name = None
                if call.is_parent:
                    agent_name = call.caller.first_name
                else:
                    agent_name = call.receiver.first_name if call.receiver else None

                # publish the event to the enduser
                pusher_data_obj = {
                    "source_event_type": "missed-call",
                    "id": str(call.call_id),
                    "sender": str(call.caller.first_name),
                    "storage_url": "",
                }
                try:
                    publish_event_to_user(
                        str(user.client.organization.token),
                        "private",
                        encode_base64(f"{call.receiver.id}"),
                        "client-event",
                        pusher_data_obj,
                    )
                except Exception as e:
                    logger.error(f"Error while publishing call scheduled event: {e}")

                try:
                    publish_event_to_channel(
                        str(user.client.organization.token),
                        "private",
                        "client-event",
                        pusher_data_obj,
                    )
                except Exception as e:
                    logger.error(
                        f"Error while publishing call scheduled event to channel: {e}"
                    )
                try:
                    organization = call.organization
                    existingEvent = Event.objects.filter(interaction_id=call.call_id)
                    if not existingEvent:
                        event = Event.create_event_async(
                            event_type=MISSED_OUR_CALL,
                            source_user_id=call.caller.id,
                            destination_user_id=call.receiver.id,
                            status=SUCCESS,
                            duration=0,
                            frontend_screen="NA",
                            agent_name=agent_name,
                            initiated_by=MANUAL,
                            interaction_type=CALL,
                            interaction_id=call.call_id,
                            is_parent=call.is_parent,
                            storage_url=call.file_url,
                            organization=organization,
                        )
                except Exception as e:
                    logger.error(f"Error while creating call event: {e}")
            return Response(
                {"message": f"Call {update_type} successfully"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Error while updating call: {e}")
            return Response(
                {"message": "Error while updating call"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ActivitiesCreateCallClientAPIView(CustomGenericAPIView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        endUserId = request.query_params.get("endUserId")
        user = User.objects.filter(id=endUserId).first()
        caller = user
        endUser = user.end_user
        receiver = None
        organization = endUser.organization
        event_type = CALL_SCHEDULED
        is_parent = False
        try:

            call = Call.create_scheduled_call(
                receiver=receiver,
                caller=caller,
                event_type=event_type,
                is_parent=is_parent,
                organization=organization,
            )

            # Now, get the auth token for client and send it to frontend.
            endUserMeetingObj = DyteMeeting.objects.filter(end_user=endUser).first()
            if not endUserMeetingObj:
                endUserMeetingObj = DyteMeeting.create_meeting(endUser)

            endUserMeetingId = endUserMeetingObj.meeting_id

            # check if the enduser auth token already exists
            endUserAuthToken = DyteAuthToken.objects.filter(
                meeting=endUserMeetingObj, is_parent=False, end_user=endUser
            ).first()

            if not endUserAuthToken:
                endUserAuthToken = DyteAuthToken.create_dyte_auth_token(
                    meeting=endUserMeetingObj,
                    is_parent=False,
                    end_user=endUser,
                )

            # publish the event to the client
            pusher_data_obj = {
                "source_event_type": "call",
                "id": str(call.call_id),
                "meeting_id": endUserMeetingId,
                "storage_url": "",
                "sender": f"{caller.first_name} {caller.last_name}",
                "company": f"{caller.end_user.company}",
                "timestamp": str(call.created_at),
                "unique_id": f"{caller.id}",
                "role": f"{caller.end_user.role}",
            }
            try:
                publish_event_to_client(
                    str(organization.token),
                    "private",
                    "enduser-event",
                    pusher_data_obj,
                )
            except Exception as e:
                logger.error(f"Error while publishing call scheduled event: {e}")

            try:
                org = call.organization
                endUser = instance.caller.end_user
                user_details = endUser.get_user_details()
                user_details_message = create_message_compact(user_details)
                message = f"User {user_details['username']} is calling :slack_call: \n {user_details_message}"

                SlackOAuthObj = SlackOAuth.objects.filter(organization=org).first()
                if SlackOAuthObj and SlackOAuthObj.is_active:
                    try:
                        Slack.post_message_to_slack_async(
                            access_token=SlackOAuthObj.access_token,
                            channel_id=SlackOAuthObj.channel_id,
                            message=message,
                        )
                    except Exception as e:
                        logger.error(f"Error while sending slack notification: 1 {e}")
                else:
                    logger.error("SlackOAuthObj not found or is inactive")
            except Exception as e:
                logger.error(f"Error while sending slack notification: {e}")

            return Response(
                {
                    "message": "Call scheduled",
                    "meeting_id": endUserMeetingId,
                    "auth_token": endUserAuthToken.token,
                    "call_id": call.call_id,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.error(f"Error while scheduling call: {e}")
            return Response(
                {"message": "Error while scheduling call"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def put(self, request, *args, **kwargs):
        endUserId = request.query_params.get("endUserId")
        call_id = request.data.get("call_id", None)
        update_type = request.data.get("update_type", None)
        if not call_id or not update_type:
            return Response(
                {"message": "call_id or update_type not provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        call = Call.objects.filter(call_id=call_id).first()
        organization = call.organization
        if not call:
            return Response(
                {"message": "Call not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            if update_type == "mark_as_missed":
                call.status = "missed"
                call.event_type = MISSED_THEIR_CALL
                call.save()

                try:
                    # send back a automated message to the endUser
                    # if the call has happend within office hours -> call_you_back_note
                    # if the call has happend outside office hours -> out_of_office_note
                    is_request_within_office_hours_bool = (
                        is_request_within_office_hours(organization)
                    )
                    if is_request_within_office_hours_bool:
                        task_id = async_task(
                            "user.tasks.send_voice_note",
                            endUserId,
                            "call_you_back_note",
                        )
                        logger.info(
                            f"Auto send voice note scheduled with task_id: {task_id}"
                        )
                    else:
                        task_id = async_task(
                            "user.tasks.send_voice_note",
                            endUserId,
                            "out_of_office_note",
                        )
                        logger.info(
                            f"Auto send voice note scheduled with task_id: {task_id}"
                        )
                except Exception as e:
                    logger.error(
                        f"Error while sending automated message to enduser: {e}"
                    )

                # send a notification to pusher
                pusher_data_obj = {
                    "source_event_type": "missed-call",
                    "id": str(call.call_id),
                    "storage_url": "",
                    "sender": f"{call.caller.first_name} {call.caller.last_name}",
                    "company": f"{call.caller.end_user.company}",
                    "timestamp": str(timezone.now()),
                    "unique_id": f"{call.caller.id}",
                    "role": f"{call.caller.end_user.role}",
                }
                try:
                    publish_event_to_client(
                        str(call.organization.token),
                        "private",
                        "enduser-event",
                        pusher_data_obj,
                    )
                except Exception as e:
                    logger.error(f"Error while publishing missed call event: {e}")

                # Create a new event type for this update
                agent_name = None
                if call.is_parent:
                    agent_name = call.caller.first_name
                else:
                    agent_name = call.receiver.first_name if call.receiver else None

                try:
                    # check if event with interaction_id already exists
                    existingEvent = Event.objects.filter(
                        interaction_id=call.call_id
                    ).first()
                    logger.info(f"\n\n\n existingEvent: {existingEvent} \n\n\n")
                    if not existingEvent:
                        event = Event.create_event_async(
                            event_type=MISSED_THEIR_CALL,
                            source_user_id=call.caller.id,
                            destination_user_id=None,
                            status=SUCCESS,
                            duration=0,
                            frontend_screen="NA",
                            agent_name=agent_name,
                            initiated_by=MANUAL,
                            interaction_type=CALL,
                            interaction_id=call.call_id,
                            is_parent=call.is_parent,
                            storage_url=call.file_url,
                            organization=organization,
                            error_stack_trace=None,
                            request_meta=None,
                        )
                except Exception as e:
                    logger.error(f"Error while creating call event: {e}")

            elif update_type == "declined_call":
                call.status = "declined"
                call.event_type = DECLINED_CALL
                call.save()

                # send a notification to pusher
                pusher_data_obj = {
                    "source_event_type": "declined-call",
                    "id": str(call.call_id),
                    "storage_url": "",
                    "sender": f"{call.caller.first_name} {call.caller.last_name}",
                    "company": f"{call.caller.end_user.company}",
                    "timestamp": str(timezone.now()),
                    "unique_id": f"{call.caller.id}",
                    "role": f"{call.caller.end_user.role}",
                }
                try:
                    publish_event_to_client(
                        str(call.organization.token),
                        "private",
                        "enduser-event",
                        pusher_data_obj,
                    )
                except Exception as e:
                    logger.error(f"Error while publishing declined call event: {e}")

                # Create a new event type for this update
                agent_name = None
                if call.is_parent:
                    agent_name = call.caller.first_name
                else:
                    agent_name = call.receiver.first_name if call.receiver else None

                try:
                    # check if event with interaction_id already exists
                    existingEvent = Event.objects.filter(
                        interaction_id=call.call_id
                    ).first()
                    logger.info(f"\n\n\n existingEvent: {existingEvent} \n\n\n")
                    if not existingEvent:
                        event = Event.create_event_async(
                            event_type=DECLINED_CALL,
                            source_user_id=call.caller.id,
                            destination_user_id=None,
                            status=SUCCESS,
                            duration=0,
                            frontend_screen="NA",
                            agent_name=agent_name,
                            initiated_by=MANUAL,
                            interaction_type=CALL,
                            interaction_id=call.call_id,
                            is_parent=call.is_parent,
                            storage_url=call.file_url,
                            organization=organization,
                            error_stack_trace=None,
                            request_meta=None,
                        )
                except Exception as e:
                    logger.error(f"Error while creating call event: {e}")
        except Exception as e:
            logger.error(f"Error while updating call: {e}")
            return Response(
                {"message": "Error while updating call"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"message": f"Call {update_type} successfully"},
            status=status.HTTP_200_OK,
        )


class EndUserListAPIView(CustomAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        organization = user.client.organization
        view_type = request.query_params.get("view_type", None)

        end_users = None
        if view_type == "all":
            end_users = EndUser.objects.filter(organization=organization)
        elif view_type == "live":
            end_users = EndUser.objects.filter(
                organization=organization, user__is_online=True
            )
        last_session_subquery = (
            EndUserSession.objects.filter(end_user=OuterRef("pk"))
            .order_by("-modified_at")
            .values("last_session_active")[:1]
        )

        queryset = (
            end_users.select_related("user")
            .prefetch_related(
                Prefetch("sessions"),
            )
            .annotate(
                last_session=Subquery(last_session_subquery),
                total_sessions_count=Count("sessions"),
            )
        )

        serialized_data = CustomEndUserSerializer(queryset, many=True)
        return Response(serialized_data.data, status=status.HTTP_200_OK)


class CalendlyWebhookAPIView(CustomAPIView):
    @csrf_exempt
    def post(self, request, *args, **kwargs):
        try:
            data = request.data
            event = data.get("event", None)
            payload = data.get("payload", None)
            scheduled_event = payload.get("scheduled_event", None)

            if event == "invitee.created":
                created_at = data.get("created_at", None)
                endUserEmail = payload.get("email")
                user = User.objects.filter(email=endUserEmail).first()
                endUser = user.end_user
                if not user:
                    return Response({"status": status.HTTP_200_OK})
                title = scheduled_event.get("name")
                start_time = scheduled_event.get("start_time")
                description = scheduled_event.get("meeting_notes_plain")
                organizer = user
                organization = endUser.organization

                # TODO, need to get the location properly

                required_date = convert_to_date(start_time, type="date")
                required_start_time = convert_to_date(start_time)
                logger.info(f"\n\n\n required_date: {required_date} \n\n\n")

                # create a new meeting object from create_meeting class method
                meeting = Meeting.create_meeting(
                    title=title,
                    start_time=required_start_time,
                    description=description,
                    organizer=organizer,
                    end_time=None,
                    location=None,
                    organization=organization,
                    date=required_date,
                )

            return Response({"status": status.HTTP_200_OK})
        except Exception as e:
            return Response({"status": "error", "error": str(e)})
