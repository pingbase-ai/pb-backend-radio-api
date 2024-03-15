from rest_framework import serializers
from .models import DyteMeeting


class DyteMeetingSerializer(serializers.ModelSerializer):
    class Meta:
        model = DyteMeeting
        fields = "__all__"
