from django.db import models
from django_q.tasks import async_task
from user.models import Organization, User


class Event(models.Model):

    # TODO should create appropirate indexes for the fields

    CALL_SCHEDULED = "CALL_SCHEDULED"
    SCHEDULED_CALL_HELD = "SCHEDULED_CALL_HELD"
    CALLED_US = "CALLED_US"
    ANSWERED_OUR_CALL = "ANSWERED_OUR_CALL"
    MISSED_OUR_CALL = "MISSED_OUR_CALL"
    MISSED_THEIR_CALL = "MISSED_THEIR_CALL"
    SENT_US_AUDIO_NOTE = "SENT_US_AUDIO_NOTE"
    WE_SENT_AUDIO_NOTE = "WE_SENT_AUDIO_NOTE"
    LOGGED_IN = "LOGGED_IN"
    LEFT_WEBAPP = "LEFT_WEBAPP"
    DECLINED_CALL = "DECLINED_CALL"

    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    AUTOMATIC = "AUTOMATIC"
    MANUAL = "MANUAL"

    CALL = "CALL"
    VOICE_NOTE = "VOICE_NOTE"
    LOGIN = "LOGIN"
    MEETING = "MEETING"

    interaction_type_choices = (
        (CALL, "Call"),
        (VOICE_NOTE, "Voice Note"),
        (LOGIN, "Login"),
        (MEETING, "Meeting"),
    )

    initiated_by_choices = ((AUTOMATIC, "Automatic"), (MANUAL, "Manual"))

    status_choices = (
        (IN_PROGRESS, "In progress"),
        (COMPLETED, "Completed"),
        (FAILED, "Failed"),
    )

    event_types = (
        (CALL_SCHEDULED, "Call scheduled"),
        (SCHEDULED_CALL_HELD, "Scheduled call held"),
        (CALLED_US, "Called us"),
        (ANSWERED_OUR_CALL, "Answered our call"),
        (MISSED_OUR_CALL, "Missed our call"),
        (MISSED_THEIR_CALL, "Missed their call"),
        (SENT_US_AUDIO_NOTE, "Sent us audio note"),
        (WE_SENT_AUDIO_NOTE, "We sent audio note"),
        (LOGGED_IN, "Logged in"),
        (LEFT_WEBAPP, "Left webapp"),
        (DECLINED_CALL, "Declined call"),
    )

    event_type = models.CharField(max_length=255, choices=event_types)
    timestamp = models.DateTimeField(auto_now_add=True)
    source_user_id = models.IntegerField(blank=True, null=True)
    destination_user_id = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=255, choices=status_choices)
    duration = models.IntegerField(blank=True, null=True)
    frontend_screen = models.CharField(max_length=255)
    request_meta = models.TextField(blank=True, null=True)
    error_stack_trace = models.TextField(blank=True, null=True)

    # new fields
    agent_name = models.CharField(max_length=255, blank=True, null=True)
    initiated_by = models.CharField(
        max_length=255, choices=initiated_by_choices, blank=True, null=True
    )
    interaction_type = models.CharField(
        max_length=255, choices=interaction_type_choices, blank=True, null=True
    )
    # FK ID to releated model of Meeting, Call, VoiceNote, EndUserLogin from
    # home.models
    interaction_id = models.CharField(max_length=255, blank=True, null=True)

    # a field to know if the interaction is completed or not, example: voice note played

    interaction_completed = models.BooleanField(default=False, blank=True, null=True)
    # Field which determines who is the parent of the event
    is_parent = models.BooleanField(default=False)

    is_seen_enduser = models.BooleanField(default=False)

    storage_url = models.URLField(max_length=2000, blank=True, null=True)

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, blank=True, null=True
    )

    # Organization level field
    is_unread = models.BooleanField(default=True)

    # enduser specific field
    is_played = models.BooleanField(default=False)

    # meeting specifi field
    scheduled_time = models.DateTimeField(blank=True, null=True)

    # Source User
    src_user = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        related_name="source_user",
        blank=True,
        null=True,
    )

    # Destination User
    dest_user = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        related_name="destination_user",
        blank=True,
        null=True,
    )

    # create a string representation for the event model
    def __str__(self):
        return self.event_type

    @classmethod
    def create_event(
        cls,
        event_type,
        source_user_id,
        destination_user_id,
        status,
        duration,
        frontend_screen,
        request_meta,
        error_stack_trace,
        agent_name=None,
        initiated_by=None,
        interaction_type=None,
        interaction_id=None,
        is_parent=False,
        storage_url=None,
        organization=None,
        scheduled_time=None,
    ):
        """
        Class method to create an Event instance.

        :param event_type: The type of the event.
        :param source_user_id: The ID of the source user.
        :param destination_user_id: The ID of the destination user.
        :param status: The status of the event.
        :param duration: Duration of the event.
        :param frontend_screen: The frontend screen where the event was triggered.
        :param request_meta: Meta information about the request.
        :param error_stack_trace: Stack trace in case of an error.
        :return: An instance of Event.
        """
        event = cls(
            event_type=event_type,
            source_user_id=source_user_id,
            destination_user_id=destination_user_id,
            status=status,
            duration=duration,
            frontend_screen=frontend_screen,
            request_meta=request_meta,
            error_stack_trace=error_stack_trace,
            agent_name=agent_name,
            initiated_by=initiated_by,
            interaction_type=interaction_type,
            interaction_id=interaction_id,
            is_parent=is_parent,
            storage_url=storage_url,
            organization=organization,
            scheduled_time=scheduled_time,
        )
        event.src_user_id = source_user_id
        event.dest_user_id = destination_user_id
        event.save()
        return event

    @staticmethod
    def create_event_async(
        event_type,
        source_user_id,
        destination_user_id,
        status,
        duration,
        frontend_screen,
        request_meta=None,
        error_stack_trace=None,
        agent_name=None,
        initiated_by=None,
        interaction_type=None,
        interaction_id=None,
        is_parent=False,
        storage_url=None,
        organization=None,
        scheduled_time=None,
    ):
        """
        Static method to create an Event instance asynchronously.

        :param event_type: The type of the event.
        :param source_user_id: The ID of the source user.
        :param destination_user_id: The ID of the destination user.
        :param status: The status of the event.
        :param duration: Duration of the event.
        :param frontend_screen: The frontend screen where the event was triggered.
        :param request_meta: Meta information about the request.
        :param error_stack_trace: Stack trace in case of an error.
        :return: None
        """
        task_id = async_task(
            Event.create_event,
            event_type,
            source_user_id,
            destination_user_id,
            status,
            duration,
            frontend_screen,
            request_meta,
            error_stack_trace,
            agent_name=agent_name,
            initiated_by=initiated_by,
            interaction_type=interaction_type,
            interaction_id=interaction_id,
            is_parent=is_parent,
            storage_url=storage_url,
            organization=organization,
            scheduled_time=scheduled_time,
        )
        return task_id
