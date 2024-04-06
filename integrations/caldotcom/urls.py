from django.urls import path
from .views import CalManagedUserCreateView, CalTokenRefreshView

urlpatterns = [
    path(
        "managed-user",
        CalManagedUserCreateView.as_view(),
        name="create_managed_user",
    ),
    path("refresh-token", CalTokenRefreshView.as_view(), name="refresh_token"),
]
