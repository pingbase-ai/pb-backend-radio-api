from django.shortcuts import render
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Event
from .serializers import EventSerializer
from infra_utils.views import CustomGenericAPIView, CustomGenericAPIListView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from user.models import Organization

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
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data)


class EventListPublicAPIView(CustomGenericAPIListView):

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
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
