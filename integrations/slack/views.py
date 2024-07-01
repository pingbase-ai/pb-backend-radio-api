import requests
from infra_utils.views import CustomAPIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from user.models import Organization
from django.shortcuts import redirect
from .models import SlackOAuth
from rest_framework.permissions import IsAuthenticated
from slack_sdk import WebClient

import urllib.parse
import json
import logging

logger = logging.getLogger("django")


# Create your views here.
# slack_url = f"https://slack.com/oauth/v2/authorize?client_id={settings.SLACK_CLIENT_ID}&scope=incoming-webhook,chat:write,chat:write.customize&redirect_uri={settings.SLACK_REDIRECT_URI}"
class SlackIntegrationAPIView(CustomAPIView):

    def get(self, request, *args, **kwargs):
        code = request.query_params.get("code", None)
        state = request.query_params.get("state", None)

        decoded_state = json.loads(urllib.parse.unquote_plus(state))
        company = decoded_state.get("company", None)
        referer = decoded_state.get("referer", None)

        try:
            response = requests.post(
                "https://slack.com/api/oauth.v2.access",
                data={
                    "client_id": settings.SLACK_CLIENT_ID,
                    "client_secret": settings.SLACK_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": settings.SLACK_REDIRECT_URI,
                },
            )
            data = response.json()
            access_token = data.get("access_token")
            channel_id = data.get("incoming_webhook").get("channel_id")

            try:
                obj, _ = SlackOAuth.objects.update_or_create(
                    organization=Organization.objects.get(name=company),
                    defaults={"access_token": access_token, "is_active": True},
                )
                obj.access_token = access_token
                obj.is_active = True
                obj.meta = data
                obj.channel_id = channel_id
                obj.save()

                try:
                    self.join_channel(access_token, channel_id)
                except Exception as e:
                    logger.error(f"Error joining channel: {e}")
                    return Response(
                        {"error": "Error while integrating slack"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

            except Organization.DoesNotExist:
                logger.error(f"Organization not found: {company}")
                return Response(
                    {"error": "Organization not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            return redirect(referer)
        except Exception as e:
            logger.error(f"Error while integrating slack: {e}")
            return Response(
                {"error": "Error while integrating slack"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @staticmethod
    def join_channel(access_token: str, channel_id: str) -> None:
        client = WebClient(token=access_token)
        try:
            response = client.conversations_join(channel=channel_id)
            print(f"Joined channel: {response['channel']['name']}")
        except Exception as e:
            print(f"Error joining channel: {e}")


class SlackAuthUrlAPIView(CustomAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company = request.query_params.get("company", None)

        referer = request.META.get(
            "HTTP_REFERER", "https://toolsvilla.app.pingbase.ai/onboarding"
        )

        logger.info(f"source_request_url: {referer}")

        if not company:
            return Response(
                {"error": "company is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        company_name = company.lower()
        organizationObj = Organization.objects.filter(name=company_name).first()
        if not organizationObj:
            return Response(
                {"error": "Organization not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            slackOAuthObj = SlackOAuth.objects.filter(
                organization=organizationObj
            ).first()

            if slackOAuthObj:
                is_slack_integration_active = slackOAuthObj.is_active
                return Response(
                    {
                        "message": "Slack integration already exists",
                        "is_active": is_slack_integration_active,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                additional_data = {"company": company_name, "referer": referer}
                state_param = urllib.parse.quote_plus(json.dumps(additional_data))

                slack_url = f"https://slack.com/oauth/v2/authorize?client_id={settings.SLACK_CLIENT_ID}&scope=incoming-webhook,chat:write,chat:write.customize,channels:join&redirect_uri={settings.SLACK_REDIRECT_URI}&state={state_param}"
                return Response({"slack_url": slack_url}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error while getting slack auth url: {e}")
            return Response(
                {"error": "Error while getting slack auth url"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def put(self, request, *args, **kwargs):
        company = request.query_params.get("company", None)
        token_status = request.data.get("status", None)
        if not company:
            return Response(
                {"error": "company is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        company_name = company.lower()
        organizationObj = Organization.objects.filter(name=company_name).first()
        if not organizationObj:
            return Response(
                {"error": "Organization not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            slackOAuthObj = SlackOAuth.objects.get(organization=organizationObj)
            slackOAuthObj.is_active = token_status
            slackOAuthObj.save()

            return Response(
                {"message": "Slack integration status changed"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Error while changing slack integration status: {e}")
            return Response(
                {"error": "Error while changing slack integration status"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
