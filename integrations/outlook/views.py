from django.shortcuts import render, redirect
from infra_utils.views import CustomGenericAPIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import OutlookOAuth
from .utils import build_msal_app
from user.models import User
from urllib.parse import quote, unquote
import json
import logging


logger = logging.getLogger("django")
REDIRECT_PATH = "https://api.pingbase.ai/api/v1/integrations/outlook/redirect"

# Create your views here.

# TODO - Need to handle token expiry


class OutlookCalendarViewInit(CustomGenericAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        user = request.user
        user_email = user.email

        # check if the user already has integration done
        outlook_oauth = OutlookOAuth.objects.filter(client=user.client).first()
        if outlook_oauth:
            return Response(
                {
                    "message": "Outlook Calendar already integrated.",
                    "is_active": outlook_oauth.is_active,
                },
                status=status.HTTP_200_OK,
            )
        msal_app = build_msal_app()

        custom_data = {
            "user_email": user_email,
            "referer": request.META.get(
                "HTTP_REFERER", "https://app.pingbase.ai/onboarding"
            ),
        }
        encoded_state = quote(json.dumps(custom_data))
        auth_url = msal_app.get_authorization_request_url(
            ["Calendars.ReadWrite"],
            redirect_uri=REDIRECT_PATH,
            response_type="code",
            state=encoded_state,
        )

        return Response({"authorization_url": auth_url}, status=status.HTTP_200_OK)


class OutlookCalendarViewRedirect(CustomGenericAPIView):
    def get(self, request, *args, **kwargs):
        code = request.GET.get("code")
        encoded_state = request.GET.get("state", "{}")
        decoded_state = json.loads(unquote(encoded_state))
        user_email = decoded_state.get("user_email")
        referer = decoded_state.get("referer")
        if not code:
            return Response(
                {"error": "Code not found in request"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        msal_app = build_msal_app()
        logger.info(f"user_email: {user_email} \n referer: {referer}")
        result = msal_app.acquire_token_by_authorization_code(
            code, scopes=["Calendars.ReadWrite"], redirect_uri=REDIRECT_PATH
        )
        logger.info(f"\n\n\n {result} \n\n\n")
        if "error" in result:
            return Response(
                {"error": result["error"]}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            user = User.objects.filter(email=user_email).first()
            outlook_oauth, _ = OutlookOAuth.objects.get_or_create(client=user.client)
            outlook_oauth.meta = json.dumps(result)
            outlook_oauth.is_active = True
            outlook_oauth.save()
            return redirect(referer)
        except Exception as e:
            logging.error(f"Error integrating Outlook Calendar: {e}")
            return Response(
                {"error": "Something went wrong"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
