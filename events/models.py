from django.db import models
from django_q.tasks import async_task


class Event(models.Model):

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
    request_meta = models.TextField()
    error_stack_trace = models.TextField(blank=True, null=True)

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
        )
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
        request_meta,
        error_stack_trace,
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
        )
        return task_id
