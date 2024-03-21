from django.shortcuts import render
from infra_utils.views import CustomGenericAPIView
from rest_framework.permissions import IsAuthenticated
from user.models import User, Client, EndUser
from rest_framework import status
from rest_framework.response import Response
from .models import DyteMeeting, DyteAuthToken
from .utils import GROUP_CALL_PARTICIPANT, GROUP_CALL_HOST
from home.models import Call
from django.db.models import Q
from home.event_types import ANSWERED_OUR_CALL
from django.conf import settings
import logging

logger = logging.getLogger("django")

# Create your views here.


class DyteMeetingView(CustomGenericAPIView):
    permission_classes = (IsAuthenticated,)

    # Retrive the meeting details of the client
    def get(self, request, *args, **kwargs):

        try:
            user = request.user
            end_user_id = request.query_params.get("end_user_id")

            if not end_user_id:
                return Response(
                    {"error": "end_user_id is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            clientUser = user.client

            endUserObj = User.objects.filter(id=end_user_id).first()
            endUser = endUserObj.end_user

            meeting = DyteMeeting.objects.filter(end_user=endUser).first()

            if not meeting:
                return Response(
                    {"error": "Meeting not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            client_auth_token_obj = DyteAuthToken.objects.filter(
                is_parent=True, client=clientUser, meeting=meeting
            ).first()

            end_user_auth_token_obj = DyteAuthToken.objects.filter(
                is_parent=False, end_user=endUser, meeting=meeting
            ).first()

            if not end_user_auth_token_obj:
                return Response(
                    {"error": "EndUser Auth Token not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if not client_auth_token_obj:
                # create a new token for the client
                try:
                    client_auth_token_obj = DyteAuthToken.create_dyte_auth_token(
                        meeting,
                        True,
                        end_user=endUser,
                        preset=GROUP_CALL_HOST,
                        client=clientUser,
                    )
                except Exception as e:
                    logger.error(f"Error while creating Dyte auth token: {e}")
                    return Response(
                        {"error": "Internal server error"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

            client_auth_token = client_auth_token_obj.token
            end_user_auth_token = end_user_auth_token_obj.token

            data = {
                "meeting": meeting.meeting_id,
                "title": meeting.title,
                "client_auth_token": client_auth_token,
                "end_user_auth_token": end_user_auth_token,
            }

            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error while getting Dyte meeting details: {e}")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DyteAuthTokenView(CustomGenericAPIView):
    permission_classes = (IsAuthenticated,)

    # Retrive the auth token details of the client
    def get(self, request, *args, **kwargs):

        try:
            user = request.user
            meeting_id = request.query_params.get("meeting_id")

            meeting = DyteMeeting.objects.filter(meeting_id=meeting_id).first()

            if not meeting_id:
                return Response(
                    {"error": "meeting_id is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            clientUser = user.client

            endUser = meeting.end_user

            if not meeting:
                return Response(
                    {"error": "Meeting not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            client_auth_token_obj = DyteAuthToken.objects.filter(
                is_parent=True, client=clientUser, meeting=meeting
            ).first()

            if not client_auth_token_obj:
                # create a new token for the client
                try:
                    client_auth_token_obj = DyteAuthToken.create_dyte_auth_token(
                        meeting,
                        True,
                        end_user=endUser,
                        preset=GROUP_CALL_HOST,
                        client=clientUser,
                    )
                except Exception as e:
                    logger.error(f"Error while creating Dyte auth token: {e}")
                    return Response(
                        {"error": "Internal server error"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

            client_auth_token = client_auth_token_obj.token

            data = {
                "meeting": meeting.meeting_id,
                "title": meeting.title,
                "client_auth_token": client_auth_token,
            }

            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error while getting Dyte auth token details: {e}")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DyteWebhookView(CustomGenericAPIView):

    def post(self, request, *args, **kwargs):

        webhookId = request.headers.get("dyte-webhook-id")

        if not webhookId:
            return Response(
                {"error": "dyte-webhook-id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if webhookId != settings.DYTE_WEBHOOK_ID:
            return Response(
                {"error": "Invalid dyte-webhook-id"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            logger.info(f"Request Data: {request.data}")
            data = request.data
            event = data.get("event")

            meetingInfo = data.get("meeting")
            meeting_id = meetingInfo.get("id")
            session_id = meetingInfo.get("sessionId")
            organizedBy = meetingInfo.get("organizedBy")

            if event == "meeting.started":

                calEvent = (
                    Call.objects.filter(
                        Q(reciver__id=int(organizedBy.id))
                        | Q(caller__id=int(organizedBy.id))
                    )
                    .filter(status="scheduled")
                    .order_by("-created_at")
                    .first()
                )

                calEvent.session_id = session_id

                return Response(
                    {"status": "success"},
                    status=status.HTTP_200_OK,
                )

            if event == "meeting.ended":

                calEvent = Call.objects.filter(session_id=session_id).first()
                calEvent.status = "completed"
                calEvent.event_type = ANSWERED_OUR_CALL
                calEvent.save()

            if event == "recording.statusUpdate":
                recording = data.get("recording")
                recordingStatus = recording.get("status")

                meeting_title = (
                    DyteMeeting.objects.filter(meeting_id=meeting_id).first().title
                )
                if recordingStatus == "UPLOADED":
                    filename = recording.get("outputFileName")
                    uploaded_url = f"{settings.AZURE_STORAGE_BLOB_URL}/{meeting_title}_{meeting_id}_{filename}"
                    calEvent = Call.objects.filter(session_id=session_id).first()
                    calEvent.file_url = uploaded_url
                    calEvent.save()
                    return Response(
                        {"status": "success"},
                        status=status.HTTP_200_OK,
                    )

            else:
                logger.info(f"Event: {event} not handled yet")
                return Response(
                    {"status": "success"},
                    status=status.HTTP_200_OK,
                )
        except Exception as e:
            logger.error(f"Error while getting Dyte auth token details: {e}")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
