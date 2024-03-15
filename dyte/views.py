from django.shortcuts import render
from infra_utils.views import CustomGenericAPIView
from rest_framework.permissions import IsAuthenticated
from user.models import User, Client, EndUser
from rest_framework import status
from rest_framework.response import Response
from .models import DyteMeeting, DyteAuthToken

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

            meeting = DyteMeeting.objects.filter(client=clientUser).first()

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

            if not client_auth_token_obj:
                return Response(
                    {"error": "Client or EndUser Auth Token not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if not end_user_auth_token_obj:
                # create a new token for the end user
                try:
                    end_user_auth_token_obj = DyteAuthToken.create_dyte_auth_token(
                        meeting, False, clientUser, end_user=endUser
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
