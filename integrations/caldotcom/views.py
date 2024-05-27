### DEPRICATED ###
import requests
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from infra_utils.views import CustomAPIView
from .models import CalDotCom

import logging

logger = logging.getLogger("django")


class CalManagedUserCreateView(CustomAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        data = {"email": user.email}
        headers = {"x-cal-secret-key": settings.CAL_DOT_COM_CLIENT_SECRET}
        url = f"https://api.cal.com/v2/oauth-clients/{settings.CAL_DOT_COM_CLIENT_ID}/users"
        response = requests.post(url, json=data, headers=headers)
        logger.info(f"\n\n\n response: {response.json()} \n\n\n")
        try:
            if response.status_code == 201:
                data = response.json()["data"]
                cal_dot_com, created = CalDotCom.objects.update_or_create(
                    client=user.client,
                    defaults={
                        "cal_user_id": data["user"]["id"],
                        "cal_atoms_access_token": data["accessToken"],
                        "cal_atoms_refresh_token": data["refreshToken"],
                    },
                )
                return Response(data)

            return Response(response.json(), status=response.status_code)
        except requests.exceptions.RequestException as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(e)
            return Response(
                {"error": "Something went wrong"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def get(self, request, *args, **kwargs):
        user = request.user
        try:
            cal_dot_com = CalDotCom.objects.get(client=user.client)
            return Response(
                {
                    "cal_user_id": cal_dot_com.cal_user_id,
                    "cal_atoms_access_token": cal_dot_com.cal_atoms_access_token,
                    "cal_atoms_refresh_token": cal_dot_com.cal_atoms_refresh_token,
                }
            )
        except CalDotCom.DoesNotExist:
            return Response(
                {"error": "Cal.com user not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(e)
            return Response(
                {"error": "Something went wrong"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CalTokenRefreshView(CustomAPIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        logger.info("\n\n\n Inside here \n\n\n")
        auth_header = request.headers.get("Authorization")
        logger.info(f"\n\n\nAuth header: {auth_header}\n\n\n")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response(
                {"error": "Authorization token required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        access_token = auth_header.split(" ")[1].replace("Bearer ", "")
        logger.info(f"\n\n\nAccess token: {access_token}\n\n\n")
        headers = {"x-cal-secret-key": settings.CAL_DOT_COM_CLIENT_SECRET}

        try:
            cal_dot_com = CalDotCom.objects.get(cal_atoms_access_token=access_token)
            refresh_url = (
                f"https://api.cal.com/v2/oauth/{settings.CAL_DOT_COM_CLIENT_ID}/refresh"
            )
            data = {
                "clientId": settings.CAL_DOT_COM_CLIENT_ID,
                "clientSecret": settings.CAL_DOT_COM_CLIENT_SECRET,
                "refreshToken": cal_dot_com.cal_atoms_refresh_token,
            }

            logger.info(
                f"\n\n\n Refresh URL: {refresh_url} \n\n\n data: {data} \n\n\n headers: {headers} \n\n\n"
            )

            response = requests.post(refresh_url, json=data, headers=headers)
            logger.info(f"\n\n\n {response.reason} \n\n\n")
            # response.raise_for_status()  # Raises HTTPError for bad responses
            data = response.json()
            logger.info(f"\n\n\n Before-data: {data} \n\n\n")

            data = data["data"]
            logger.info(f"\n\n\n after-data: {data} \n\n\n")

            cal_dot_com.cal_atoms_access_token = data["accessToken"]
            cal_dot_com.cal_atoms_refresh_token = data["refreshToken"]
            cal_dot_com.save()
            return Response({"accessToken": data["accessToken"]})

        except CalDotCom.DoesNotExist:
            return Response(
                {"error": "Token invalid or expired"}, status=status.HTTP_404_NOT_FOUND
            )
        except requests.exceptions.RequestException as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
