from django.shortcuts import render
from infra_utils.views import CustomGenericAPIView
from rest_framework.permissions import IsAuthenticated
from user.models import User, Client, EndUser, Organization
from rest_framework import status
from rest_framework.response import Response
from .models import DyteMeeting, DyteAuthToken
from .utils import GROUP_CALL_PARTICIPANT, GROUP_CALL_HOST
from home.models import Call
from django.db.models import Q
from home.event_types import ANSWERED_OUR_CALL
from django.conf import settings
from events.models import Event
from infra_utils.utils import get_time_difference
from june import analytics
from infra_utils.constants import BE_CALL_AGENT, BE_CALL_ENDUSER

import logging

logger = logging.getLogger("django")
analytics.write_key = settings.JUNE_API_KEY
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


class DytePublicAuthTokenView(CustomGenericAPIView):

    # Retrive the auth token details of the enduser
    def get(self, request, *args, **kwargs):

        org_token = request.headers.get("organization-token")
        if not org_token:
            return Response(
                {"error": "organization" "token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        orgObj = Organization.objects.filter(token=org_token).first()
        if not orgObj:
            return Response(
                {"error": "Organization not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            endUserId = request.query_params.get("endUserId")
            user = User.objects.filter(id=endUserId).first()
            endUser = user.end_user

            if not endUser:
                return Response(
                    {"error": "EndUser not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            meeting = DyteMeeting.objects.filter(end_user=endUser).first()
            authToken = DyteAuthToken.objects.filter(
                is_parent=False, end_user=endUser, meeting=meeting
            ).first()

            if not authToken:
                # create a new token for the enUser
                try:
                    authToken = DyteAuthToken.create_dyte_auth_token(
                        meeting,
                        False,
                        end_user=endUser,
                        preset=GROUP_CALL_PARTICIPANT,
                        client=None,
                    )
                except Exception as e:
                    logger.error(f"Error while creating Dyte auth token: {e}")
                    return Response(
                        {"error": "Internal server error"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

            data = {
                "meeting": meeting.meeting_id,
                "title": meeting.title,
                "end_user_auth_token": authToken.token,
            }

            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error while getting Dyte auth token details: {e}")
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
                # before creating make sure all the client cache is deleted from dyte
                # try:
                #     DyteAuthToken.delete_dyte_auth_token(user.id, meeting_id)
                # except Exception as e:
                #     logger.error(f"Error while deleting Dyte auth token: {e}")
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
            if event == "meeting.ended":
                # {'event': 'meeting.ended', 'meeting': {'id': 'bbbc3e70-0b5f-43da-bb20-680c11ee2495', 'sessionId': '51d3062f-63eb-487d-ba6f-f463ccf7e234', 'title': 'Self - End user', 'status': 'LIVE', 'createdAt': '2024-04-10T08:55:36.514Z', 'startedAt': '2024-04-10T08:55:36.514Z', 'endedAt': '2024-04-10T08:56:44.887Z', 'organizedBy': {'id': 'c61c65d0-8c01-4103-8797-7400fbb8d8b4', 'name': 'Pingbaseai'}}, 'reason': 'ALL_PARTICIPANTS_LEFT'}
                try:
                    calEvent = Call.objects.filter(session_id=session_id).first()
                    if calEvent:
                        calEvent.status = "completed"
                        # calEvent.event_type = ANSWERED_OUR_CALL
                        calEvent.save()

                        # send a June.so event for tracking
                        started_at = meetingInfo.get("startedAt")
                        ended_at = meetingInfo.get("endedAt")

                        # reducing 60 seconds cause of dyte's internal implementation
                        init_recorded_time = abs(
                            get_time_difference(started_at, ended_at) - 60
                        )
                        if calEvent.is_parent:
                            try:
                                user = calEvent.caller
                                client = calEvent.caller.client
                                analytics.identify(
                                    user_id=str(user.id),
                                    traits={
                                        "email": user.email,
                                        "firstName": user.first_name,
                                        "lastName": user.last_name,
                                        "role": client.role,
                                        "department": client.department,
                                        "job_title": client.job_title,
                                        "orgKey": client.organization.token,
                                        "userType": "AGENT",
                                    },
                                )
                                analytics.track(
                                    user_id=str(user.id),
                                    event=BE_CALL_AGENT,
                                    properties={
                                        "session_id": str(session_id),
                                        "object": {
                                            "endUser": {
                                                "id": calEvent.receiver.id,
                                                "email": calEvent.receiver.email,
                                                "first_name": calEvent.receiver.first_name,
                                                "last_name": calEvent.receiver.last_name,
                                            },
                                            "length": f"{init_recorded_time}",
                                        },
                                    },
                                )
                            except Exception as e:
                                logger.error(f"Error while sending June event: {e}")
                        else:
                            try:
                                user = calEvent.caller
                                end_user = calEvent.caller.end_user
                                analytics.identify(
                                    user_id=str(user.id),
                                    traits={
                                        "email": user.email,
                                        "firstName": user.first_name,
                                        "lastName": user.last_name,
                                        "role": end_user.role,
                                        "industry": end_user.company,
                                        "plan": end_user.trial_type,
                                        "orgKey": end_user.organization.token,
                                        "userType": "ENDUSER",
                                    },
                                )

                                analytics.track(
                                    user_id=str(user.id),
                                    event=BE_CALL_ENDUSER,
                                    properties={
                                        "session_id": str(session_id),
                                        "object": {
                                            "endUser": {
                                                "id": calEvent.caller.id,
                                                "email": calEvent.caller.email,
                                                "first_name": calEvent.caller.first_name,
                                                "last_name": calEvent.caller.last_name,
                                            },
                                            "length": f"{init_recorded_time}",
                                        },
                                    },
                                )
                            except Exception as e:
                                logger.error(f"Error while sending June event: {e}")
                    return Response(
                        {"status": "success"},
                        status=status.HTTP_200_OK,
                    )
                except Exception as e:
                    logger.error(f"Error while updating status of Call {e}")
                    return Response(
                        {"error": "Something went wrong"},
                        status=status.HTTP_200_OK,
                    )

            if event == "recording.statusUpdate":
                recording = data.get("recording")
                recordingStatus = recording.get("status")

                if recordingStatus == "UPLOADED":
                    try:
                        filename = recording.get("outputFileName").replace(" ", "")
                        uploaded_url = f"{settings.DYTE_AZURE_BLOB_URL}/{filename}"
                        calEvent = Call.objects.filter(session_id=session_id).first()
                        calEvent.file_url = uploaded_url
                        calEvent.save()

                        # update the event with this uploaded_url

                        event = Event.objects.filter(
                            interaction_id=calEvent.call_id
                        ).first()
                        if event:
                            event.storage_url = uploaded_url
                            event.save()

                        return Response(
                            {"status": "success"},
                            status=status.HTTP_200_OK,
                        )
                    except Exception as e:
                        logger.error(f"Error while updating file_url of Call {e}")
                        return Response(
                            {"error": "Something went wrong"},
                            status=status.HTTP_200_OK,
                        )
                else:
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
