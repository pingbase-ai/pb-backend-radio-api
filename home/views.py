from django.shortcuts import render
from rest_framework.views import APIView
from infra_utils.views import CustomAPIView, CustomGenericAPIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework.permissions import IsAuthenticated
from .serializers import (
    MeetingSerializer,
    CallSerializer,
    VoiceNoteSerializer,
    EndUserLoginSerializer,
)
from .models import Meeting, Call, VoiceNote, EndUserLogin
from user.models import Client, User
from .utils import upload_to_azure_blob
from django.db.models import Q
from rest_framework.parsers import FileUploadParser
from .event_types import WE_SENT_AUDIO_NOTE, SENT_US_AUDIO_NOTE
import logging
import datetime
import uuid


logger = logging.getLogger("django")


# Create your views here.
class TasksClientAPIView(CustomAPIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):

        user = request.user

        client = Client.objects.filter(user=user).first()
        if not client:
            return Response(
                {"message": "Client not found for the user"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        organization = client.organization
        # Retrieve Meeting, Call, and Voice Notes data for the client
        meetings = Meeting.objects.filter(
            organization=organization, attendees=user, status="scheduled"
        )
        calls = Call.objects.filter(organization=organization, is_seen=False)
        voice_notes = VoiceNote.objects.filter(organization=organization, is_seen=False)

        # Return the serialized data as a response
        return Response(
            {
                "meetings": meetings.count(),
                "calls": calls.count(),
                "voice_notes": voice_notes.count(),
            }
        )


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
    parser_classes = (FileUploadParser,)

    def post(self, request, filename, *args, **kwargs):
        user = request.user

        endUserId = request.query_params.get("end_user_id")

        sender = user
        reciver = User.objects.filter(id=endUserId).first()
        file = request.FILES["file"]
        if not file:
            return Response(
                {"message": "File not provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        audio_file_url = upload_to_azure_blob(
            file,
            f"voice-notes/{user.client.organization.name}",
            f"voice_note_{uuid.uuid4()}.webm",
        )
        logger.info(f"\n\n\n {audio_file_url} \n\n\n")

        try:
            voice_note = VoiceNote.create_voice_note(
                sender=sender,
                reciver=reciver,
                audio_file_url=audio_file_url,
                description=request.data.get("description", ""),
                organization=user.client.organization,
                event_type=WE_SENT_AUDIO_NOTE,
            )
            voice_note.mark_as_seen(user)
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
    parser_classes = (FileUploadParser,)

    def post(self, request, filename, *args, **kwargs):

        endUserId = request.query_params.get("endUserId")
        user = User.objects.filter(id=endUserId).first()
        sender = user
        reciver = None
        file = request.FILES["file"]
        if not file:
            return Response(
                {"message": "File not provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        audio_file_url = upload_to_azure_blob(
            file,
            f"voice-notes/{user.end_user.organization.name}",
            f"voice_note_{uuid.uuid4()}.webm",
        )
        logger.info(f"\n\n\n {audio_file_url} \n\n\n")

        try:
            voice_note = VoiceNote.create_voice_note(
                sender=sender,
                reciver=reciver,
                audio_file_url=audio_file_url,
                description=request.data.get("description", ""),
                organization=user.end_user.organization,
                event_type=SENT_US_AUDIO_NOTE,
            )
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
