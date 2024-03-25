import requests
from infra_utils.views import CustomAPIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

import logging

logger = logging.getLogger("django")


# Create your views here.
# slack_url = f"https://slack.com/oauth/v2/authorize?client_id={settings.SLACK_CLIENT_ID}&scope=incoming-webhook,chat:write,chat:write.customize&redirect_uri={settings.SLACK_REDIRECT_URI}"
class SlackIntegrationAPIView(CustomAPIView):
    def get(self, request, *args, **kwargs):
        code = request.query_params.get("code", None)
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
        logger.info(f"Response from slack: {data}")

        return Response(
            {"message": "Slack integration successful"}, status=status.HTTP_200_OK
        )


class SlackAuthUrlAPIView(CustomAPIView):
    def get(self, request, *args, **kwargs):
        slack_url = f"https://slack.com/oauth/v2/authorize?client_id={settings.SLACK_CLIENT_ID}&scope=incoming-webhook,chat:write,chat:write.customize&redirect_uri={settings.SLACK_REDIRECT_URI}"
        return Response({"slack_url": slack_url}, status=status.HTTP_200_OK)
