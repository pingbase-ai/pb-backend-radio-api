# base_types.py

VOICE_NOTE = "VOICE_NOTE"
CALL_SCHEDULED = "CALL_SCHEDULED"
CALL_HELD = "CALL_HELD"
MISSED_CALL = "MISSED_CALL"

# base output types
SUCCESS = "SUCCESS"
FAILURE = "FAILURE"
IN_PROGRESS = "IN_PROGRESS"


# initated by
AUTOMATIC = "AUTOMATIC"
MANUAL = "MANUAL"

# interaction types
CALL = "CALL"
LOGIN = "LOGIN"
MEETING = "MEETING"
# VOICE_NOTE = "VOICE_NOTE"

# event_types.py

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

EVENT_TYPE_CHOICES = [
    (CALL_SCHEDULED, "Call Scheduled"),
    (SCHEDULED_CALL_HELD, "Scheduled Call Held"),
    (CALLED_US, "Called Us"),
    (ANSWERED_OUR_CALL, "Answered Our Call"),
    (MISSED_OUR_CALL, "Missed Our Call"),
    (MISSED_THEIR_CALL, "Missed Their Call"),
    (SENT_US_AUDIO_NOTE, "Sent Us Audio Note"),
    (WE_SENT_AUDIO_NOTE, "We Sent Audio Note"),
    (LOGGED_IN, "Logged In"),
    (DECLINED_CALL, "Declined Call"),
]


GROUPED_EVENT_TYPES = [
    (VOICE_NOTE, "Voice Note"),
    (CALL_SCHEDULED, "Call Scheduled"),
    (CALL_HELD, "Call Held"),
    (MISSED_CALL, "Missed Call"),
]
