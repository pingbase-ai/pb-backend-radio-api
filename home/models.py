from django.db import models
from user.models import User, Organization, EndUser
from infra_utils.models import CreatedModifiedModel
import uuid
from .event_types import EVENT_TYPE_CHOICES, CALL_SCHEDULED
from django_q.tasks import async_task


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
    location = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
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
        max_length=255, choices=EVENT_TYPE_CHOICES, default=CALL_SCHEDULED
    )

    # Field to differentiate between Client and Enduser Organizer
    is_parent = models.BooleanField(default=False)

    scheduled_at = models.DateTimeField(auto_now_add=True)
    session_id = models.CharField(max_length=255, blank=True, null=True)
    file_url = models.URLField(max_length=2000, blank=True, null=True)

    def __str__(self):
        return self.title

    @classmethod
    def create_meeting(
        cls,
        title,
        date,
        start_time,
        end_time,
        location,
        description,
        organizer,
        organization,
    ):
        meeting = cls(
            title=title,
            date=date,
            start_time=start_time,
            end_time=end_time,
            location=location,
            description=description,
            organization=organization,
            organizer=organizer,
        )
        meeting.attendees.add(organizer)
        meeting.save()

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

    receiver = models.ForeignKey(
        User,
        related_name="received_calls",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.DO_NOTHING, related_name="calls"
    )

    start_time = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
    )
    event_type = models.CharField(
        max_length=255, choices=EVENT_TYPE_CHOICES, default="Called Us"
    )
    # Field to differentiate between Client and Enduser Organizer
    is_parent = models.BooleanField(default=False)
    file_url = models.URLField(max_length=2000, blank=True, null=True)
    session_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Call from {self.caller} on {self.start_time}"

    def mark_as_seen(self, user):
        self.is_seen = True
        self.seen_by.add(user)
        self.save()

    @classmethod
    def create_scheduled_call(
        cls, receiver, caller, event_type, is_parent, organization
    ):
        call = cls(
            receiver=receiver,
            caller=caller,
            status="scheduled",
            event_type=event_type,
            is_parent=is_parent,
            organization=organization,
        )
        call.save()
        return call


class VoiceNote(CreatedModifiedModel):

    voice_note_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    is_seen_enduser = models.BooleanField(default=False)
    is_seen = models.BooleanField(default=False)
    seen_by = models.ManyToManyField(
        User,
        related_name="seen_voice_notes",
        blank=True,
    )
    sender = models.ForeignKey(
        User, related_name="voice_notes", on_delete=models.DO_NOTHING
    )
    receiver = models.ForeignKey(
        User,
        related_name="received_voice_notes",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
    )

    organization = models.ForeignKey(
        Organization, on_delete=models.DO_NOTHING, related_name="voice_notes"
    )

    audio_file_url = models.URLField(max_length=2000, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(null=True, blank=True)

    event_type = models.CharField(
        max_length=255, choices=EVENT_TYPE_CHOICES, default="Sent Us Audio Note"
    )
    # Field to differentiate between Client and Enduser Organizer
    is_parent = models.BooleanField(default=False)

    def __str__(self):
        return f"VoiceNote from {self.sender} at {self.created_at}"

    def mark_as_seen(self, user):
        self.is_seen = True
        self.seen_by.add(user)
        self.save()

    @classmethod
    def create_voice_note(
        cls,
        sender,
        receiver,
        audio_file_url,
        organization,
        is_parent,
        description="",
        event_type="",
    ):
        voice_note = cls(
            sender=sender,
            receiver=receiver,
            audio_file_url=audio_file_url,
            description=description,
            organization=organization,
            event_type=event_type,
            is_parent=is_parent,
        )
        voice_note.save()
        return voice_note


class EndUserLogin(CreatedModifiedModel):
    login_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    end_user = models.ForeignKey(
        EndUser, on_delete=models.CASCADE, related_name="logins"
    )
    last_login = models.DateTimeField(auto_now=True)
    organization = models.ForeignKey(
        Organization, on_delete=models.DO_NOTHING, related_name="end_user_logins"
    )
    event_type = models.CharField(max_length=255, default="Logged In")
    is_seen = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.end_user} + {self.last_login}"

    @staticmethod
    def create_login(end_user, organization):
        login = EndUserLogin(end_user=end_user, organization=organization)
        return login

    @staticmethod
    def create_login_async(end_user, organization):
        task_id = async_task(EndUserLogin.create_login, end_user, organization)

        return task_id
