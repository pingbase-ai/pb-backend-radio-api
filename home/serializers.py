from rest_framework import serializers
from .models import Meeting, Call, VoiceNote, EndUserLogin
from user.serializers import EndUserSerializer


class MeetingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meeting
        fields = [
            "title, date, start_time, end_time, location, description, attendees, status, organizer"
        ]


class CallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Call
        fields = [
            "caller",
            "scheduled_time",
            "start_time",
            "end_time",
            "status",
            "is_seen",
        ]


class VoiceNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoiceNote
        fields = ["sender", "audio_file", "created_at", "description"]


class EndUserLoginSerializer(serializers.ModelSerializer):
    end_user = EndUserSerializer()

    class Meta:
        model = EndUserLogin
        fields = ["end_user", "last_login", "organization"]
