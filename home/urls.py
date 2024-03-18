from . import views
from django.urls import path

urlpatterns = [
    path(
        "client/tasks/", views.TasksClientAPIView.as_view(), name="retrive_tasks_list"
    ),
    path(
        "client/activity/",
        views.ActivitiesCreateModifyClientAPIView.as_view(),
        name="create_modify_client_activities",
    ),
    path(
        "client/activity/list/<slug:tab>",
        views.ActivitiesClientAPIView.as_view(),
        name="retrieve_client_activities_list",
    ),
    # used in widget UI
    path(
        "end_user/activity/list/",
        views.ActivitiesEndUserAPIView.as_view(),
        name="retrieve_end_user_activities_list",
    ),
    # used in widget UI
    path(
        "end_user/activity/",
        views.ActivitiesCreateModifyEndUserAPIView.as_view(),
        name="create_modify_end_user_activities",
    ),
]
