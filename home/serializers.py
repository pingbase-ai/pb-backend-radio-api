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
            "start_time",
            "end_time",
            "status",
            "is_seen",
            "event_type",
            "is_parent",
        ]


class VoiceNoteSerializer(serializers.ModelSerializer):

    sender = serializers.SerializerMethodField()
    reciver = serializers.SerializerMethodField()

    def get_sender(self, obj):
        if obj.sender:
            return obj.sender.first_name

        return ""

    def get_reciver(self, obj):
        if obj.reciver:
            return obj.reciver.first_name
        return ""

    class Meta:
        model = VoiceNote
        fields = [
            "voice_note_id",
            "sender",
            "audio_file_url",
            "created_at",
            "description",
            "reciver",
            "event_type",
        ]


class EndUserLoginSerializer(serializers.ModelSerializer):
    end_user = EndUserSerializer()

    class Meta:
        model = EndUserLogin
        fields = ["end_user", "last_login", "organization"]
