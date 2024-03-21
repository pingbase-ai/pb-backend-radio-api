from . import views
from django.urls import path, re_path

urlpatterns = [
    path(
        "client/tasks/", views.TasksClientAPIView.as_view(), name="retrive_tasks_list"
    ),
    path(
        "client/activity/",
        views.ActivitiesCreateModifyClientAPIView.as_view(),
        name="create_modify_client_activities",
    ),
    # client sending voice note
    re_path(
        r"^client/activity/voice-note/upload/(?P<filename>[^/]+)$",
        views.ActivitiesCreateVoiceNoteClientAPIView.as_view(),
        name="create_modify_voice_note_client_activities",
    ),
    # client viewing/ editing voice note
    path(
        "client/activity/voice-note",
        views.ActivitiesViewModifyVoiceNoteClientAPIView.as_view(),
        name="view_modify_voice_note_client_activities",
    ),
    # end user sending voice note
    re_path(
        r"^end-user/activity/voice-note/upload/(?P<filename>[^/]+)$",
        views.ActivitiesCreateVoiceNoteEndUserAPIView.as_view(),
        name="create_modify_voice_note_enduser_activities",
    ),
    # end user viewing/ updating voice note
    path(
        "end-user/activity/voice-note",
        views.ActivitiesViewVoiceNoteEndUserAPIView.as_view(),
        name="view_voice_note_enduser_activities",
    ),
    # client calling the enduser
    path(
        "client/activity/call",
        views.ActivitiesCreateViewModifyCallEndUserAPIView.as_view(),
        name="create_modify_update_call_enduser",
    ),
    # enduser calling the client
    path(
        "end-user/activity/call",
        views.ActivitiesCreateCallClientAPIView.as_view(),
        name="create_call_client",
    ),
    path(
        "client/activity/list/<slug:tab>",
        views.ActivitiesClientAPIView.as_view(),
        name="retrieve_client_activities_list",
    ),
    # used in widget UI
    path(
        "end-user/activity/list/",
        views.ActivitiesEndUserAPIView.as_view(),
        name="retrieve_end_user_activities_list",
    ),
    # used in widget UI
    path(
        "end-user/activity/",
        views.ActivitiesCreateModifyEndUserAPIView.as_view(),
        name="create_modify_end_user_activities",
    ),
]
