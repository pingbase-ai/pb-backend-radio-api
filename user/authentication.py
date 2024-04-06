from django.urls import resolve
from rest_framework_simplejwt.authentication import JWTAuthentication


class SelectiveJWTAuthentication(JWTAuthentication):
    UNAUTHENTICATED_PATHS = [
        "api/v1/integrations/cal/refresh-token",
    ]  # List of paths to allow unauthenticated access

    def authenticate(self, request):
        # Get the current path
        current_path = resolve(request.path_info).route

        # Check if the current path is in the list of unauthenticated paths
        if current_path in self.UNAUTHENTICATED_PATHS:
            return None

        # Proceed with the standard JWT authentication for other paths
        return super().authenticate(request)
