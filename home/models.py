from django.db import models
from user.models import User, Organization, EndUser
from infra_utils.models import CreatedModifiedModel
import uuid
from .event_types import EVENT_TYPE_CHOICES


# Create your models here.
class Meeting(CreatedModifiedModel):

    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("missed", "Missed"),
        ("completed", "Completed"),
    ]

    meeting_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField(null=True, blank=True)
    location = models.CharField(max_length=100)
    description = models.TextField()
    attendees = models.ManyToManyField(User, related_name="attendees")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="Scheduled"
    )
    organizer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="organizer"
    )

    organization = models.ForeignKey(
        Organization, on_delete=models.DO_NOTHING, related_name="meetings"
    )

    event_type = models.CharField(
        max_length=255, choices=EVENT_TYPE_CHOICES, default="Call Scheduled"
    )

    def __str__(self):
        return self.title

    @classmethod
    def create_meeting(
        cls, title, date, start_time, end_time, location, description, organizer
    ):
        meeting = cls(
            title=title,
            date=date,
            start_time=start_time,
            end_time=end_time,
            location=location,
            description=description,
        )
        meeting.save()
        # Assuming 'organizer' is a User instance who is organizing the meeting
        meeting.attendees.add(organizer)
        return meeting

    def add_attendee(self, user):
        self.attendees.add(user)
        self.save()


class Call(CreatedModifiedModel):
    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("missed", "Missed"),
        ("completed", "Completed"),
    ]

    call_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_seen = models.BooleanField(default=False)
    seen_by = models.ManyToManyField(User, related_name="seen_calls", blank=True)
    caller = models.ForeignKey(
        User, related_name="made_calls", on_delete=models.DO_NOTHING
    )

    reciver = models.ForeignKey(
        User,
        related_name="received_calls",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.DO_NOTHING, related_name="calls"
    )

    scheduled_time = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
    )
    event_type = models.CharField(
        max_length=255, choices=EVENT_TYPE_CHOICES, default="Called Us"
    )

    def __str__(self):
        return f"Call from {self.caller} on {self.scheduled_time}"

    def mark_as_seen(self, user):
        self.is_seen = True
        self.seen_by.add(user)
        self.save()

    @classmethod
    def create_scheduled_call(cls, receiver, caller, scheduled_time):
        call = cls(
            receiver=receiver,
            caller=caller,
            scheduled_time=scheduled_time,
            status="scheduled",
        )
        call.save()
        return call


class VoiceNote(CreatedModifiedModel):

    voice_note_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    is_seen = models.BooleanField(default=False)
    seen_by = models.ManyToManyField(
        User,
        related_name="seen_voice_notes",
        blank=True,
    )
    sender = models.ForeignKey(
        User, related_name="voice_notes", on_delete=models.DO_NOTHING
    )
    reciver = models.ForeignKey(
        User,
        related_name="received_voice_notes",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
    )

    organization = models.ForeignKey(
        Organization, on_delete=models.DO_NOTHING, related_name="voice_notes"
    )
    # TODO Need to fully integrate storage service with audio files
    audio_file = models.FileField(upload_to="voice_notes/")
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(null=True, blank=True)

    event_type = models.CharField(
        max_length=255, choices=EVENT_TYPE_CHOICES, default="Sent Us Audio Note"
    )

    def __str__(self):
        return f"VoiceNote for {self.reciver} at {self.created_at}"

    def mark_as_seen(self, user):
        self.is_seen = True
        self.seen_by.add(user)
        self.save()

    @classmethod
    def create_voice_note(cls, sender, reciver, audio_file, description=""):
        voice_note = cls(
            sender=sender,
            reciver=reciver,
            audio_file=audio_file,
            description=description,
        )
        voice_note.save()
        return voice_note


class EndUserLogin(CreatedModifiedModel):
    login_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    end_user = models.OneToOneField(EndUser, on_delete=models.CASCADE)
    last_login = models.DateTimeField(auto_now=True)
    Organization = models.ForeignKey(
        Organization, on_delete=models.DO_NOTHING, related_name="end_user_logins"
    )
    event_type = models.CharField(max_length=255, default="Logged In")

    def __str__(self):
        return f"{self.end_user} + {self.last_login}"

    @classmethod
    def create_login(cls, end_user):
        login = cls(end_user=end_user)
        login.save()
        return login
