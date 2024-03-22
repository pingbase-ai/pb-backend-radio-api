from rest_framework import serializers
from .models import Event
from user.models import User


class CustomEventSerializer(serializers.ModelSerializer):

    event_type = serializers.SerializerMethodField()
    source_user_id = serializers.SerializerMethodField()
    destination_user_id = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    frontend_screen = serializers.SerializerMethodField()
    request_meta = serializers.SerializerMethodField()
    error_stack_trace = serializers.SerializerMethodField()
    agent_name = serializers.SerializerMethodField()
    initiated_by = serializers.SerializerMethodField()
    interaction_type = serializers.SerializerMethodField()
    interaction_id = serializers.SerializerMethodField()
    is_parent = serializers.SerializerMethodField()
    source_username = serializers.SerializerMethodField()
    destination_username = serializers.SerializerMethodField()
    timestamp = serializers.SerializerMethodField()

    def get_event_type(self, obj):
        return obj.event_type

    def get_source_user_id(self, obj):
        return obj.source_user_id

    def get_destination_user_id(self, obj):
        return obj.destination_user_id

    def get_status(self, obj):
        return obj.status

    def get_duration(self, obj):
        return obj.duration

    def get_frontend_screen(self, obj):
        return obj.frontend_screen

    def get_request_meta(self, obj):
        return obj.request_meta

    def get_error_stack_trace(self, obj):
        return obj.error_stack_trace

    def get_agent_name(self, obj):
        return obj.agent_name

    def get_initiated_by(self, obj):
        return obj.initiated_by

    def get_interaction_type(self, obj):
        return obj.interaction_type

    def get_interaction_id(self, obj):
        return obj.interaction_id

    def get_is_parent(self, obj):
        return obj.is_parent

    def get_source_username(self, obj):
        if obj.source_user_id:
            username = User.objects.filter(id=obj.source_user_id).first().first_name
            return username
        return ""

    def get_destination_username(self, obj):
        if obj.destination_user_id:
            username = (
                User.objects.filter(id=obj.destination_user_id).first().first_name
            )
            return username
        return ""

    def get_timestamp(self, obj):
        return obj.timestamp

    class Meta:
        model = Event
        fields = [
            "event_type",
            "source_user_id",
            "destination_user_id",
            "status",
            "duration",
            "frontend_screen",
            "request_meta",
            "error_stack_trace",
            "agent_name",
            "initiated_by",
            "interaction_type",
            "interaction_id",
            "is_parent",
            "source_username",
            "destination_username",
            "timestamp",
        ]


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = "__all__"
