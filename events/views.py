from django.shortcuts import render
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Event
from .serializers import EventSerializer, CustomEventSerializer, CustomEventSerializerV1
from infra_utils.views import CustomGenericAPIView, CustomGenericAPIListView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from user.models import Organization


import logging

logger = logging.getLogger("django")

# Create your views here.


class EventCreateAPIView(CustomGenericAPIView):
    def post(self, request, *args, **kwargs):
        serializer = EventSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EventListAPIView(CustomGenericAPIListView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        user = request.user
        endUserId = request.query_params.get("endUserId")
        events = Event.objects.filter(
            Q(source_user_id=endUserId) | Q(destination_user_id=endUserId)
        )
        serializer = CustomEventSerializer(events, many=True)
        return Response(serializer.data)


class EventListTypeAPIView(CustomGenericAPIListView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, type, *args, **kwargs):
        user = request.user
        client = user.client

        organization = client.organization

        if type == "all":
            events = Event.objects.filter(
                organization=organization,
            )
            serializer = CustomEventSerializerV1(events, many=True)
            return Response(serializer.data)
        else:
            Response({"error": "Invalid type"}, status=status.HTTP_400_BAD_REQUEST)


class EventUpdateAPIView(CustomGenericAPIView):
    permission_classes = (IsAuthenticated,)

    def put(self, request, *args, **kwargs):
        user = request.user
        organization = user.client.organization
        try:
            event = Event.objects.filter(organization=organization).update(
                is_unread=False
            )
            return Response(
                {"message": f"All Events marked as read <-> {event}"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Error while updating event: {e}")
            return Response(
                {"error": "Something went wrong!"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class EventListPublicAPIView(CustomGenericAPIListView):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):

        organization_token = request.headers.get("organization-token")

        if not organization_token:
            return Response(
                {"error": "organization-token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        organizationObj = Organization.objects.filter(token=organization_token).first()
        if not organizationObj:
            return Response(
                {"error": "Organization not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        endUserId = request.query_params.get("endUserId")
        events = Event.objects.filter(
            Q(source_user_id=endUserId) | Q(destination_user_id=endUserId)
        )
        serializer = CustomEventSerializer(events, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EventPublicAPIView(CustomGenericAPIView):

    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        organization_token = request.headers.get("organization-token")
        endUserId = request.query_params.get("endUserId")

        if not organization_token:
            return Response(
                {"error": "organization-token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not endUserId:
            return Response(
                {"error": "endUserId is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        organizationObj = Organization.objects.filter(token=organization_token).first()
        if not organizationObj:
            return Response(
                {"error": "Organization not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        unseen_events = Event.objects.filter(
            destination_user_id=endUserId,
            is_seen_enduser=False,
            event_type__in=[
                "CALLED_US",
                "ANSWERED_OUR_CALL",
                "MISSED_OUR_CALL",
                "WE_SENT_AUDIO_NOTE",
                "SENT_US_AUDIO_NOTE",
            ],
        )
        unseen_events_count = unseen_events.count()

        # new events
        new_events = Event.objects.filter(
            destination_user_id=endUserId,
            is_seen_enduser=False,
            event_type__in=[
                "MISSED_OUR_CALL",
                "WE_SENT_AUDIO_NOTE",
            ],
        )
        new_events_count = new_events.count()
        last_recored_obj = {}

        last_record = (
            Event.objects.filter(
                destination_user_id=endUserId,
                event_type__in=["MISSED_OUR_CALL", "WE_SENT_AUDIO_NOTE"],
            )
            .order_by("-timestamp")
            .first()
        )

        if last_record:
            if last_record.is_seen_enduser is False:
                serializer = CustomEventSerializer(last_record)
                last_recored_obj = serializer.data

        return Response(
            {
                "unseen_events_count": unseen_events_count,
                "new_events_count": new_events_count,
                "last_record": last_recored_obj,
            },
            status=status.HTTP_200_OK,
        )

    def put(self, request, *args, **kwargs):

        organization_token = request.headers.get("organization-token")
        endUserId = request.query_params.get("endUserId")
        eventId = request.query_params.get("eventId")

        if not organization_token:
            return Response(
                {"error": "organization-token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        organizationObj = Organization.objects.filter(token=organization_token).first()
        if not organizationObj:
            return Response(
                {"error": "Organization not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not eventId:
            event = Event.objects.filter(
                destination_user_id=endUserId,
                is_seen_enduser=False,
                event_type__in=[
                    "CALLED_US",
                    "ANSWERED_OUR_CALL",
                    "MISSED_OUR_CALL",
                    "WE_SENT_AUDIO_NOTE",
                    "SENT_US_AUDIO_NOTE",
                ],
            ).update(is_seen_enduser=True)
        else:
            event = Event.objects.filter(id=eventId).first()
            event.is_seen_enduser = True
            event.is_played = True
        if not event:
            return Response(
                {"error": "Event not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        event.is_seen_enduser = True
        event.save()
        return Response(
            {"message": "All Events marked as seen"}, status=status.HTTP_200_OK
        )
