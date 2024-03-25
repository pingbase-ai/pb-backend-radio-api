import requests
from infra_utils.views import CustomAPIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

import logging

logger = logging.getLogger("django")


# Create your views here.
class SlackIntegrationAPIView(CustomAPIView):
    def get(self, request, *args, **kwargs):
        # Return the slack integration page
        slack_url = f"https://slack.com/oauth/v2/authorize?client_id={settings.SLACK_CLIENT_ID}&scope=incoming-webhook&redirect_uri={settings.SLACK_REDIRECT_URI}"

        return Response({"slack_url": slack_url}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        # Your code logic here
        code = request.GET.get("code")
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
