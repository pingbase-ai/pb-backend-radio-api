from django.shortcuts import render
from rest_framework import generics, status, views, permissions
from .models import PusherChannelApp  # Import the missing serializer class

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from user.models import Client, Organization, EndUser, User
from django.views.decorators.csrf import csrf_exempt
from events.models import Event
from django.utils import timezone

from rest_framework.request import Request
from .utils import publish_event_to_pusher, PusherClientSingleton
from infra_utils.views import CustomGenericAPIView, CustomAPIView

from infra_utils.utils import decode_base64
from django.conf import settings
from home.models import EndUserLogin
from .constants import ENDUSER, CLIENT

import logging
import json

logger = logging.getLogger("django")


# Create your views here.

# create a view to retrieve PusherChannelApp object based on the organization

# Import the missing Response class


class PusherChannelAppView(APIView):  # Fix the base class type

    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):  # Add the return type annotation

        user = request.user
        client = Client.objects.filter(user=user).first()
        organization = client.organization

        if organization:
            pusher_app_obj = PusherChannelApp.objects.filter(
                organization=organization
            ).first()
            if pusher_app_obj:
                return Response(
                    {
                        "app_id": pusher_app_obj.app_id,
                        "key": pusher_app_obj.key,
                        "secret": pusher_app_obj.secret,
                        "cluster": pusher_app_obj.cluster,
                        "SSL": pusher_app_obj.SSL,
                        "app_name": pusher_app_obj.app_name,
                        "app_description": pusher_app_obj.app_description,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"error": "No Pusher App found for this organization"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            return Response(
                {"error": "No organization found for this user"},
                status=status.HTTP_404_NOT_FOUND,
            )


class PusherChannelAppCompanyView(generics.GenericAPIView):  # Fix the base class type

    def post(
        self,
        request,
    ):  # Add the return type annotation

        data = request.data
        print(data)
        company_name = data.get("company_name")
        end_user_id = data.get("end_user_id")

        Enduser = EndUser.objects.filter(id=int(end_user_id)).first()

        if not Enduser:
            return Response(
                {"error": "No EndUser found with this user"},
                status=status.HTTP_404_NOT_FOUND,
            )

        organization = Organization.objects.filter(name=company_name).first()

        if organization:
            pusher_app_obj = PusherChannelApp.objects.filter(
                organization=organization
            ).first()
            if pusher_app_obj:
                return Response(
                    {
                        "app_id": pusher_app_obj.app_id,
                        "key": pusher_app_obj.key,
                        "secret": pusher_app_obj.secret,
                        "cluster": pusher_app_obj.cluster,
                        "SSL": pusher_app_obj.SSL,
                        "app_name": pusher_app_obj.app_name,
                        "app_description": pusher_app_obj.app_description,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"error": "No Pusher App found for this organization"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            return Response(
                {"error": "No organization found for this user"},
                status=status.HTTP_404_NOT_FOUND,
            )


class PusherChannelAppWebhookPresenceView(generics.GenericAPIView):

    def post(self, request):

        # pusher_client = PusherClientSingleton().get_client()
        pusher_key: str = request.headers.get("X-Pusher-Key")

        verified_request = PusherClientSingleton().verify_pusher_key(pusher_key)

        # TODO implement this fully
        # webhook = pusher_client.validate_webhook(
        #     key=request.headers.get("X-Pusher-Key"),
        #     signature=request.headers.get("X-Pusher-Signature"),
        #     body=data,
        # )
        webhook = request.data
        processed_user_ids = set()

        logger.info(f"\n\n\n webhook_data: {webhook} \n\n\n")

        if verified_request:
            for event in webhook["events"]:

                organization = None

                channel = event["channel"]
                name = event["name"]
                user_id = event["user_id"]
                if user_id in processed_user_ids:
                    continue
                processed_user_ids.add(user_id)

                userObj = User.objects.filter(id=user_id).first()

                endUser = None
                if hasattr(userObj, "end_user"):
                    endUser = userObj.end_user
                    if endUser:
                        organization = endUser.organization

                if name == "member_added":
                    # create a new EndUserLogin instance if the last EndUserLogin instance timestamp diff is greater than 1 hour
                    if endUser:

                        last_login = (
                            EndUserLogin.objects.filter(end_user=endUser)
                            .order_by("-created_at")
                            .first()
                        )
                        if not last_login or (
                            (timezone.now() - last_login.created_at).total_seconds()
                            > 3600
                        ):
                            logger.info(
                                f"\n\n\n creating login event for {endUser} \n\n\n"
                            )
                            # Create a new EndUserLogin instance
                            async_id = EndUserLogin.create_login_async(
                                endUser, organization
                            )

                    # set user status to active
                    userObj.set_online_status(True)

                elif name == "member_removed":
                    userObj.set_online_status(False)

            return Response(
                {"status": "success"},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"error": "Unauthorized request"},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class ClientPusherChannelAppPublishView(generics.GenericAPIView):

    permission_classes = [IsAuthenticated]

    def post(self, request: Request):  # Add the return type annotation

        user = request.user
        client = Client.objects.filter(user=user).first()
        organization = client.organization

        if organization:
            result = publish_event_to_pusher(
                client.organization, request.data, request.META
            )
            return Response(
                {
                    "status": result.get("status", ""),
                    "error": result.get("error", ""),
                },
                status=result.get("http_status"),
            )
        else:
            return Response(
                {"error": "No organization found for this user"},
                status=status.HTTP_404_NOT_FOUND,
            )


class EndUserPusherChannelPublishView(APIView):
    """
    API view to handle messages published by end users.
    """

    def post(self, request: Request) -> Response:
        # Extract the token and other data from the request
        token = request.headers.get("Authorization")
        data = request.data

        if not token:
            return Response(
                {"error": "Authorization token is required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Verify the token and get the associated organization
        organization = Organization.objects.filter(token=token).first()
        if not organization:
            return Response(
                {"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED
            )

        # From here, you would retrieve or verify the end_user based on your business logic
        # For example, you might include an end_user identifier in the request data
        end_user_id = data.get("end_user_id")
        if not end_user_id:
            return Response(
                {"error": "End user ID is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        end_user = EndUser.objects.filter(
            user__id=end_user_id, organization=organization
        ).first()
        if not end_user:
            return Response(
                {"error": "Invalid end user"}, status=status.HTTP_404_NOT_FOUND
            )
        result = publish_event_to_pusher(organization, data, request.META)
        return Response(
            {
                "status": result.get("status", ""),
                "error": result.get("error", ""),
            },
            status=result.get("http_status"),
        )


class PusherAuth(APIView):
    def post(self, request, *args, **kwargs):
        # Initialize Pusher

        pusher = PusherClientSingleton(
            app_id=settings.PUSHER_APP_ID,
            key=settings.PUSHER_KEY,
            secret=settings.PUSHER_SECRET,
            cluster=settings.PUSHER_CLUSTER,
        )

        user_token = request.headers.get("X-User-Token")

        data = request.data

        user_id = user_token.split("-")[0]
        username = user_token.split("-")[1]

        # Assume the user is authenticated via Django's session auth

        auth = pusher.authenticate(
            channel=data["channel_name"],
            socket_id=data["socket_id"],
            custom_data={"user_id": user_id, "user_info": {"name": username}},
        )
        print(f"auth: {auth}")
        return Response(auth, status=status.HTTP_200_OK)
        # if request.user.is_authenticated:
        #     user_id = str(request.user.id)  # Unique identifier for the user
        #     user_info = {"name": request.user.username}  # Example user info

        #     auth = pusher.authenticate(
        #         channel=request.data["channel_name"],
        #         socket_id=request.data["socket_id"],
        #         custom_data={"user_id": user_id, "user_info": username},
        #     )
        #     return Response(auth, status=status.HTTP_200_OK)
        # else:
        #     return Response(
        #         {"message": "User is not authenticated"},
        #         status=status.HTTP_403_FORBIDDEN,
        #     )


class PusherUserAuth(APIView):
    def post(self, request, *args, **kwargs):
        data = request.data

        user_token = request.headers.get("X-User-Token")

        user_id = decode_base64(user_token)

        socket_id = data.get("socket_id")
        channel = data.get("channel_name")

        logger.info(f"channel -- {channel}")

        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        username = user.first_name or "Anonymous"

        user_type = None
        if hasattr(user, "end_user"):
            user_type = ENDUSER
        else:
            user_type = CLIENT

        pusher_client = PusherClientSingleton().get_client()

        user = {
            "user_id": user_id,
            "user_info": {"name": username, "user_type": user_type},
        }

        logger.info(f"pusher_client: {dir(pusher_client)}")

        auth = pusher_client.authenticate(
            channel=channel, socket_id=socket_id, custom_data=user
        )
        return Response(auth, status=status.HTTP_200_OK)


class PusherEventPublish(CustomAPIView):
    def post(self, request, *args, **kwargs):
        data = request.data
        channel = data.get("channel")
        event_type = data.get("event_type")
        message = data.get("message")
        source_user_id = data.get("source_user_id")
        destination_user_id = data.get("destination_user_id")
        status_ = data.get("status")
        frontend_screen = data.get("frontend_screen")
        socket_id = data.get("socket_id", None)

        pusher_client = PusherClientSingleton().get_client()

        try:
            pusher_client.trigger(
                channel, event_type, {"message": f"{message}"}, socket_id
            )
            # Event.create_event_async(
            #     event_type=event_type,
            #     source_user_id=source_user_id,
            #     destination_user_id=destination_user_id,
            #     status=status_,
            #     duration=None,  # Consider making this parameterized as well
            #     frontend_screen=frontend_screen,
            #     request_meta=request.META,
            #     error_stack_trace=None,
            # )
            return Response(
                {"status": "success", "http_status": status.HTTP_200_OK},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            # Event.create_event_async(
            #     event_type=event_type,
            #     source_user_id=source_user_id,
            #     destination_user_id=destination_user_id,
            #     status="FAILED",
            #     duration=None,
            #     frontend_screen=frontend_screen,
            #     request_meta=request.META,
            #     error_stack_trace=str(e),
            # )
            logger.info(f"Error: {str(e)}")
            return Response(
                {"http_status": status.HTTP_500_INTERNAL_SERVER_ERROR},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ClientSendMessage(CustomAPIView):
    def post(self, request, *args, **kwargs):
        data = request.data

        channel = data.get("channel")
        event_type = data.get("event_type")
        message = data.get("message")
        source_user_id = data.get("source_user_id")
        destination_user_id = data.get("destination_user_id")
        socket_id = data.get("socket_id")

        pusher_client = PusherClientSingleton().get_client()

        try:
            pusher_client.trigger(channel, event_type, {"message": f"{message}"})
            return Response(
                {"status": "Message sent", "http_status": status.HTTP_200_OK},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.info(f"Error: {str(e)}")
            return Response(
                {"http_status": status.HTTP_500_INTERNAL_SERVER_ERROR},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
