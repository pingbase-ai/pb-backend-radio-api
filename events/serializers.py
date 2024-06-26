from rest_framework import serializers
from .models import Event
from user.models import User
from user.serializers import CustomEndUserSerializer
from home.models import EndUserSession

import logging

logger = logging.getLogger("django")


class CustomEventSerializerV1(serializers.ModelSerializer):
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
    sub_event_type = serializers.SerializerMethodField()

    enduser_id = serializers.SerializerMethodField()
    enduser_first_name = serializers.SerializerMethodField()
    enduser_last_name = serializers.SerializerMethodField()
    enduser_is_online = serializers.SerializerMethodField()
    enduser_last_login = serializers.SerializerMethodField()
    enduser_email = serializers.SerializerMethodField()
    enduser_last_session_login = serializers.SerializerMethodField()
    enduser_is_new = serializers.SerializerMethodField()
    enduser_phone = serializers.SerializerMethodField()

    enduser_role = serializers.SerializerMethodField()
    enduser_company = serializers.SerializerMethodField()
    enduser_sessions = serializers.SerializerMethodField()
    enduser_trail_type = serializers.SerializerMethodField()
    enduser_linkedin = serializers.SerializerMethodField()
    enduser_checkin_status = serializers.SerializerMethodField()

    storage_url = serializers.SerializerMethodField()
    is_seen_enduser = serializers.SerializerMethodField()
    is_played = serializers.SerializerMethodField()
    is_unread = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

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
        return obj.src_user.first_name if obj.src_user else None

    def get_destination_username(self, obj):
        return obj.dest_user.first_name if obj.dest_user else None

    def get_timestamp(self, obj):
        return obj.timestamp

    def get_enduser_id(self, obj):
        user = obj.dest_user if obj.is_parent else obj.src_user
        if user:
            return user.id
        return None

    def get_enduser_first_name(self, obj):
        user = obj.dest_user if obj.is_parent else obj.src_user
        return user.first_name if user else None

    def get_enduser_last_name(self, obj):
        user = obj.dest_user if obj.is_parent else obj.src_user
        return user.last_name if user else None

    def get_enduser_is_online(self, obj):
        user = obj.dest_user if obj.is_parent else obj.src_user
        return user.is_online if user else None

    def get_enduser_last_login(self, obj):
        user = obj.dest_user if obj.is_parent else obj.src_user
        return user.last_login if user else None

    def get_enduser_last_session_login(self, obj):
        try:
            if obj.is_parent:
                return obj.dest_last_session
            else:
                return obj.src_last_session
        except Exception as e:
            logger.error(f"Error while fetching last session login: {e}")
            return None

    def get_enduser_role(self, obj):
        user = obj.dest_user if obj.is_parent else obj.src_user
        return user.end_user.role if user else None

    def get_enduser_email(self, obj):
        user = obj.dest_user if obj.is_parent else obj.src_user
        return user.email if user else None

    def get_enduser_company(self, obj):
        user = obj.dest_user if obj.is_parent else obj.src_user
        return user.end_user.company if user else None

    def get_enduser_sessions(self, obj):
        user = obj.dest_user if obj.is_parent else obj.src_user
        return user.end_user.total_sessions if user else None

    def get_enduser_trail_type(self, obj):
        user = obj.dest_user if obj.is_parent else obj.src_user
        return user.end_user.trial_type if user else None

    def get_enduser_linkedin(self, obj):
        user = obj.dest_user if obj.is_parent else obj.src_user
        return user.end_user.linkedin if user else None

    def get_storage_url(self, obj):
        return obj.storage_url

    def get_is_seen_enduser(self, obj):
        return obj.is_seen_enduser

    def get_is_played(self, obj):
        return obj.is_played

    def get_is_unread(self, obj):
        return obj.is_unread

    def get_enduser_is_new(self, obj):
        try:
            user = obj.dest_user if obj.is_parent else obj.src_user
            return user.end_user.is_new if user else False
        except Exception as e:
            logger.error(f"Error while fetching is_new: {e}")
            return False

    def get_enduser_checkin_status(self, obj):
        try:
            user = obj.dest_user if obj.is_parent else obj.src_user
            return user.end_user.check_in_status if user else False
        except Exception as e:
            logger.error(f"Error while fetching check_in_status: {e}")
            return False

    def get_name(self, obj):
        return obj.name if obj.name else None

    def get_sub_event_type(self, obj):
        return obj.sub_event_type

    def get_enduser_phone(self, obj):
        user = obj.dest_user if obj.is_parent else obj.src_user
        return user.phone if user else None

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
            "enduser_id",
            "enduser_first_name",
            "enduser_last_name",
            "enduser_is_online",
            "enduser_last_login",
            "enduser_last_session_login",
            "enduser_role",
            "enduser_email",
            "enduser_company",
            "enduser_sessions",
            "enduser_trail_type",
            "enduser_linkedin",
            "enduser_is_new",
            "enduser_checkin_status",
            "storage_url",
            "is_seen_enduser",
            "is_played",
            "is_unread",
            "name",
            "sub_event_type",
            "enduser_phone",
        ]


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
    sub_event_type = serializers.SerializerMethodField()

    storage_url = serializers.SerializerMethodField()
    is_seen_enduser = serializers.SerializerMethodField()
    is_played = serializers.SerializerMethodField()
    is_unread = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

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

    def get_storage_url(self, obj):
        return obj.storage_url

    def get_is_seen_enduser(self, obj):
        return obj.is_seen_enduser

    def get_is_played(self, obj):
        return obj.is_played

    def get_is_unread(self, obj):
        return obj.is_unread

    def get_name(self, obj):
        return obj.name if obj.name else None

    def get_sub_event_type(self, obj):
        return obj.sub_event_type

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
            "storage_url",
            "is_seen_enduser",
            "is_played",
            "is_unread",
            "name",
            "sub_event_type",
        ]


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = "__all__"
