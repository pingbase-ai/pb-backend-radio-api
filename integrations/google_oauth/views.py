# Description: This file contains the views for the Google OAuth integration.
# Create your views here.
from django.shortcuts import redirect


from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import GoogleOAuth
from .utils import credentials_to_dict
from infra_utils.views import CustomGenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from user.models import User
from .constants import API_SERVICE_NAME, API_VERSION
from .utils import ensure_credentials_file

import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import os
import json
import logging
import urllib.parse

logger = logging.getLogger("django")

CLIENT_SECRETS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    ensure_credentials_file(),
)

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
# This variable specifies the name of a file that contains the OAuth 2.0
# information for this application, including its client_id and client_secret.
# CLIENT_SECRETS_FILE = "credentials.json"

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection and REDIRECT URL.
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid",
]
REDIRECT_URL = "http://127.0.0.1:8000/api/v1/integrations/google/redirect"


class GoogleCalendarViewInit(CustomGenericAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        logger.info(f"CLIENT_SECRETS_FILE -- {CLIENT_SECRETS_FILE}")
        user = request.user
        user_email = user.email

        # check if the user already has integration done
        google_oauth = GoogleOAuth.objects.filter(client=user.client).first()
        if google_oauth:
            return Response(
                {
                    "message": "Google Calendar already integrated.",
                    "is_active": google_oauth.is_active,
                },
                status=status.HTTP_200_OK,
            )

        referer = request.META.get("HTTP_REFERER", "https://app.pingbase.ai/onboarding")
        # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=SCOPES
        )

        # The URI created here must exactly match one of the authorized redirect URIs
        # for the OAuth 2.0 client, which you configured in the API Console. If this
        # value doesn't match an authorized URI, you will get a 'redirect_uri_mismatch'
        # error.
        flow.redirect_uri = REDIRECT_URL
        custom_data = {
            "user_email": user_email,
            "referer": referer,
        }
        state_param = json.dumps(custom_data)
        # encoded_state = json.dumps(state_param)

        authorization_url, state = flow.authorization_url(
            # Enable offline access so that you can refresh an access token without
            # re-prompting the user for permission. Recommended for web server apps.
            access_type="offline",
            # Enable incremental authorization. Recommended as a best practice.
            include_granted_scopes="true",
            state=state_param,
        )

        logger.info(f"state -- {state}")
        request.session["state"] = state

        return Response(
            {"authorization_url": authorization_url}, status=status.HTTP_200_OK
        )


class GoogleCalendarViewRedirect(CustomGenericAPIView):
    def get(self, request, *args, **kwargs):

        # Specify the state when creating the flow in the callback so that it can
        # verify in the authorization server response.
        state = request.query_params.get("state", None)
        decoded_state = json.loads((state))
        logger.info(f"decoded-state: {decoded_state}")

        user_email = decoded_state.get("user_email", None)
        referer = decoded_state.get("referer", None)
        if state is None or user_email is None:
            return Response({"error": "State or user parameter missing."})

        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=SCOPES, state=state
        )
        flow.redirect_uri = REDIRECT_URL

        # Use the authorization server's response to fetch the OAuth 2.0 tokens.
        authorization_response = request.get_full_path()
        flow.fetch_token(authorization_response=authorization_response)

        credentials = flow.credentials

        # save credentials to the database
        user = User.objects.filter(email=user_email).first()
        if not user:
            logger.error(f"User not found with email: {user_email}")

        try:
            googleOAuthObj, created = GoogleOAuth.objects.get_or_create(
                client=user.client,
                defaults={"meta": json.dumps(credentials_to_dict(credentials))},
            )
            googleOAuthObj.meta = json.dumps(credentials_to_dict(credentials))
            googleOAuthObj.is_active = True
            googleOAuthObj.save()
        except Exception as e:
            logger.error(f"Error while saving google credentials: {e}")

        return redirect(referer)


class GoogleCalendarEventsView(CustomGenericAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        user = request.user
        google_oauth = GoogleOAuth.objects.filter(client=user.client).first()
        if not google_oauth:
            return Response(
                {"error": "Google OAuth not found for the user"},
                status=status.HTTP_404_NOT_FOUND,
            )

        credentials = google.oauth2.credentials.Credentials(
            **json.loads(google_oauth.meta)
        )

        # Use the Google API Discovery Service to build client libraries, IDE plugins,
        # and other tools that interact with Google APIs.
        # The Discovery API provides a list of Google APIs and a machine-readable "Discovery Document" for each API
        service = googleapiclient.discovery.build(
            API_SERVICE_NAME, API_VERSION, credentials=credentials
        )

        # Returns the calendars on the user's calendar list
        calendar_list = service.calendarList().list().execute()

        # Getting user ID which is his/her email address
        calendar_id = calendar_list["items"][0]["id"]

        # Getting all events associated with a user ID (email address)
        events = service.events().list(calendarId=calendar_id).execute()

        events_list_append = []
        if not events["items"]:
            print("No data found.")
            return Response({"message": "No data found or user credentials invalid."})
        else:
            for events_list in events["items"]:
                events_list_append.append(events_list)

        return Response({"events": events_list_append}, status=status.HTTP_200_OK)
