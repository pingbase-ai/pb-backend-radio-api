from .serializers import (
    RegistrationSerializer,
    EmailVerificationSerializer,
    ResendVerificationEmailSerializer,
    LoginSerializer,
    RequestPasswordResetEmailSerializer,
    SetNewPasswordSerializer,
    UserSerializer,
    LogoutSerializer,
    EndUserListSerializer,
    CheckInFeatureSerializer,
)
from rest_framework.response import Response
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth import get_user_model
from django.urls import reverse
from .utils import (
    Mail,
    remove_spaces_from_text,
    schedule_active_status_for_client,
    validate_check_in_status,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import generics, status, views, permissions
from django.conf import settings
import jwt
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import smart_bytes, smart_str, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse
from home.utils import upload_to_azure_blob
from home.models import Meeting
from .models import (
    Organization,
    Client,
    OfficeHours,
    WelcomeNote,
    CallYouBackNote,
    OutOfOfficeNote,
    Widget,
    EndUser,
    CheckInFeature,
    UserSession,
)
from pusher_channel_app.models import PusherChannelApp
from .serializers import (
    EndUserSerializer,
    OfficeHoursSerializer,
    WidgetSerializer,
    WelcomeNoteSerializer,
    CallYouBackNoteSerializer,
    OutOfOfficeNoteSerializer,
    ClientSerializer,
    OrganizationSerializer,
    SetNewPasswordAdhocSerializer,
    ClientMemberSerializer,
    CustomEndUserSerializer,
    FeatureFlagConnectSerializer,
    CheckInFeatureSerializer,
)
from infra_utils.views import (
    CustomAPIView,
    CustomGenericAPIView,
    CustomGenericAPIListView,
)
from infra_utils.utils import password_rule_check, generate_strong_password
from django.db.models import Q, Prefetch
from django.shortcuts import redirect
from .constants import (
    get_integration_code_snippet,
    get_new_app_signup_slack_block_template_part_1,
    get_new_app_signup_slack_block_template_part_2,
    get_new_app_signup_slack_block_template_part_3,
    SKIPPED,
    NOT_APPLICABLE,
    COMPLETED,
    CHECKIN_SKIPPED,
    CHECKIN_COMPLETED,
    CHECKIN_NOT_APPLICABLE,
)
from home.models import EndUserLogin, EndUserSession
from django.utils import timezone
from user.tasks import send_slack_blocks_async
from dyte.utils import replace_special_chars
from events.models import Event
from home.event_types import SUCCESS, AUTOMATIC, VOICE_NOTE, MANUAL

import logging
import json
import datetime

User = get_user_model()
logger = logging.getLogger("django")

# Create your views here.


class APIRootView(CustomAPIView):
    """
    API root view that redirects to various other endpoints.
    """

    def get(self, request, *args, **kwargs):
        return Response({"data": "Hello world"}, status=status.HTTP_200_OK)


class SignUpView(CustomGenericAPIView):

    serializer_class = RegistrationSerializer

    def get(self, request, type, *args, **kwargs):

        if type == "check":
            email = request.query_params.get("email", None)
            company_name = request.query_params.get("company", None)

            if not email or not company_name:
                return Response(
                    {"message": "Email and company name are required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                user = User.objects.filter(email=email).first()
                client = Client.objects.filter(user=user).first()
                if not user or not client:
                    return Response(
                        {"message": "User/client does not exist."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if str(client.organization.name).lower() != str(company_name).lower():
                    return Response(
                        {"message": "User does not belong to the company."},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                return Response(
                    {"message": "Check passed"},
                    status=status.HTTP_200_OK,
                )
            except Exception as e:
                logger.error(f"Error: {e}")
                return Response(
                    {"message": "Something went wrong"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        if type == "invitee":
            return Response(
                {"message": "User does not exist."},
                status=status.HTTP_200_OK,
            )
        email = request.GET.get("email")
        logger.info(f"Email: {email}")

        user = User.objects.filter(email=email).first()
        if user:
            client = Client.objects.filter(user=user).first()
            has_active_subscription = client.organization.subscriptions.filter(
                is_active=True
            ).exists()
            return Response(
                {
                    "message": "User already exists.",
                    "has_active_subscription": has_active_subscription,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            return Response(
                {"message": "User does not exist."},
                status=status.HTTP_200_OK,
            )

    def post(self, request, type, *args, **kwargs):

        data = request.data
        email = data.get("email")
        password = data.get("password")
        company = data.get("company")

        if not email or not password or not company:
            return Response(
                {"message": "Email, password and company name are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if type == "invitee":
            user = User.objects.filter(email=email).first()

            try:
                if not password_rule_check(password):
                    return Response(
                        {
                            "message": "Password must contain at least 8 characters, at least one uppercase letter, one lowercase letter, one number and one special character",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                user.set_password(password)
                user.save()
                return Response(
                    {"message": "Password set successfully."}, status=status.HTTP_200_OK
                )
            except Exception as e:
                logger.error(f"Error: {e}")
                return Response(
                    {"message": "Something went wrong, please try again later"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        else:
            try:
                if not password_rule_check(password):
                    return Response(
                        {
                            "message": "Password must contain at least 8 characters, at least one uppercase letter, one lowercase letter, one number and one special character",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                user = User.objects.filter(email=email).first()

                if user:
                    return Response(
                        {"message": "User already exists."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                    # client = Client.objects.filter(user=user).first()
                    # if client:
                    #     return Response(
                    #         {"message": "Client already exists."},
                    #         status=status.HTTP_400_BAD_REQUEST,
                    #     )

                # first create an organization with company name
                # check if the organization exists already
                organization = Organization.objects.filter(name=company).first()

                if organization:
                    return Response(
                        {"message": "Organization already exists."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if not organization:
                    final_company_name = replace_special_chars(company)
                    organization = Organization.objects.create(name=final_company_name)
                    organization.save()

                # create the user
                serializer = self.serializer_class(data=data)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                user_data = serializer.data

                ####  Sending email
                user = User.objects.get(email=user_data["email"])

                token = RefreshToken.for_user(user).access_token

                current_site_domain = get_current_site(request).domain
                relativeLink = reverse("verify-email")

                verification_link = (
                    "https://"
                    + current_site_domain
                    + relativeLink
                    + "?token="
                    + str(token)
                )

                message = "Hit the link below to verify your email and activate your PingBase account."
                html_email_body = (
                    f"Hi,<br><br>"
                    f"{message}<br><br>"
                    f"<a href='{verification_link}'>Activate your PingBase account</a>"
                    f"<br><br>Thanks,<br>Team PingBase<br>"
                )
                # email_body = "Hi " + user.email + message + verification_link
                data = {
                    "html_email_body": html_email_body,
                    "to_email": user.email,
                    "email_subject": "Verify your email",
                    "email_body": None,
                }
                try:
                    Mail.send_email(data)
                except Exception as e:
                    logger.error(f"Error: {e}")

                client = Client.objects.filter(user=user).first()

                if not client:
                    client = Client.objects.create(
                        user=user,
                        organization=organization,
                        role="admin",
                    )
                    client.save()

                # send a notification to slack
                blocks = [
                    *get_new_app_signup_slack_block_template_part_1(),
                    *get_new_app_signup_slack_block_template_part_2(company, email),
                    *get_new_app_signup_slack_block_template_part_3(),
                ]
                slack_hook = settings.SLACK_APP_SIGNUPS_WEBHOOK_URL

                data = {
                    "blocks": blocks,
                    "slack_hook": slack_hook,
                }
                try:
                    send_slack_blocks_async(data)
                except Exception as e:
                    logger.error(
                        f"Error while sending slack notification from view: {e}"
                    )

                return Response(user_data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response(
                    {"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )


class MemberList(CustomGenericAPIListView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        user = request.user
        user_id = user.id

        company_name = user.client.organization.name

        all_members = (
            Client.objects.filter(organization__name=company_name)
            .exclude(user__id=user_id)
            .filter(user__is_active=True, user__is_verified=True)
        )

        serializer = ClientMemberSerializer(all_members, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        user = request.user

        user_id = request.data.get("user_id")
        role = request.data.get("role")

        if user.id == user_id:
            return Response(
                {"message": "You cannot change your own role"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            member = Client.objects.filter(user__id=user_id).first()
            member.role = role
            member.save()
        except Exception as e:
            logger.error(f"Error: {e}")
            return Response(
                {"message": "Something went wrong"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"message": "Role changed successfully"},
            status=status.HTTP_200_OK,
        )

    def delete(self, request, *args, **kwargs):
        user = request.user

        user_id = request.data.get("user_id")

        if user.id == user_id:
            return Response(
                {"message": "You cannot delete yourself"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            member = Client.objects.filter(user__id=user_id).first()
            # Instead of deleting the user, we will just deactivate the user
            member.user.is_active = False
            member.user.is_verified = False
            member.user.save()
        except Exception as e:
            logger.error(f"Error: {e}")
            return Response(
                {"message": "Something went wrong"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"message": "User deleted successfully"},
            status=status.HTTP_200_OK,
        )


class InviteTeamateView(CustomGenericAPIView):

    serializer_class = RegistrationSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, type, *args, **kwargs):
        data = request.data
        email = data.get("email")
        company = data.get("company")
        invitee_email = data.get("invitee_email")

        referer: str = request.META.get(
            "HTTP_REFERER", "https://toolsvilla.toolsvilla.app.pingbase.ai/onboarding"
        )

        ClientInvitee = Client.objects.filter(user__email=invitee_email).first()

        if not ClientInvitee:
            return Response(
                {"message": "Invitee does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        password = generate_strong_password()

        data["password"] = password

        organization = Organization.objects.filter(name=company).first()
        if not organization:
            return Response(
                {"message": "Organization does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        user = User.objects.filter(email=email).first()
        if user:
            client = Client.objects.filter(user=user).first()
            if client:
                return Response(
                    {"message": "Client already exists."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # create the user
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        user_data = serializer.data

        # Sending Email
        user = User.objects.get(email=user_data["email"])

        token = RefreshToken.for_user(user).access_token

        current_site_domain = get_current_site(request).domain
        relativeLink = reverse("verify-email")
        verification_link = (
            "https://" + current_site_domain + relativeLink + "?token=" + str(token)
        )
        # Add logic to send a dedicated email for onboarding
        total_org_clients = Client.objects.filter(organization=organization).count()
        logger.info(
            f"total_org_clients -{total_org_clients}",
        )
        logger.info(f"referer -{referer}")
        if total_org_clients == 1 or "onboarding" in referer.lower():
            # this means, it's the invite to get onboarded
            message = f"Your colleague, whose email is {request.user.email}, has signed up for PingBase and would like you to complete the onboarding. Click on the link below to get started:"
            html_email_body = (
                f"Hi there,<br><br>"
                f"{message}<br><br>"
                f"<a href='{verification_link}'>Complete PingBase onboarding</a>"
                f"<br><br>Thanks,<br>Team PingBase<br>"
            )
            # email_body = "Hi " + user.email + message + verification_link
            data = {
                "html_email_body": html_email_body,
                "to_email": user.email,
                "email_subject": "You've been invited to setup PingBase",
                "email_body": None,
            }
            try:
                Mail.send_email(data)
            except Exception as e:
                logger.error(f"Error: {e}")
        else:
            message = f"You've been served an invite to join Pingbase by {request.user.email}!"

            html_email_body = (
                f"Hi there,<br><br>"
                f"{message}<br><br>"
                f"Use the link below to verify your email and get started:"
                f"<a href='{verification_link}'>Click here to get started</a>"
                f"<br><br>Thanks,<br>Team PingBase<br>"
            )
            data = {
                "email_body": None,
                "to_email": user.email,
                "email_subject": "You’ve been invited to PingBase",
                "html_email_body": html_email_body,
            }
            try:
                Mail.send_email(data)
            except Exception as e:
                logger.error(f"Error: {e}")

        client = Client.objects.filter(user=user).first()

        if not client:
            if type == "admin":
                client = Client.objects.create(
                    user=user,
                    organization=organization,
                    role="admin",
                )
            else:
                client = Client.objects.create(
                    user=user,
                    organization=organization,
                    role="standard_user",
                )

            client.save()

        # if onboarded_by is not set then set to this user
        try:
            if not organization.onboarded_by:
                organization.onboarded_by = client
                organization.save()
        except Exception as e:
            logger.error(f"Error while setting onboarded_by: {e}")

        return Response(user_data, status=status.HTTP_201_CREATED)


class ProfileView(CustomGenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, type):
        user = request.user
        if type == "client":
            # prefetch the organization
            client = (
                Client.objects.prefetch_related(
                    "organization",
                    "organization__client_banners",
                    "organization__office_hours",
                )
                .filter(user=user)
                .first()
            )

            if not client:
                return Response(
                    {"message": "Client doesn't exist"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            serializer = ClientSerializer(client)
            return Response(serializer.data, status=status.HTTP_200_OK)
        # elif type == "organization":
        #     organization = Organization.objects.filter(name=user.organization).first()
        #     if not organization:
        #         return Response(
        #             {"message": "Organization doesn't exist"},
        #             status=status.HTTP_404_NOT_FOUND,
        #         )
        #     serializer = OrganizationSerializer(organization)
        #     return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"message": "Invalid profile type"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def put(self, request, type):
        user = request.user
        data = request.data
        if type == "client":
            client = Client.objects.filter(user=user).first()
            if not client:
                return Response(
                    {"message": "Client doesn't exist"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            first_name = data.get("firstName")
            last_name = data.get("lastName")
            department = data.get("department")
            jobTitle = data.get("jobTitle")

            try:
                user.first_name = first_name
                user.last_name = last_name

                client.department = department
                client.job_title = jobTitle

                user.save()
                client.save()

                return Response(status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Error: {e}")
                return Response(
                    {"message": "Something went wrong"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        else:
            return Response(
                {"message": "Invalid profile type"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ProfilePicView(CustomGenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        user = request.user
        file = request.FILES.get("file")
        if not file:
            return Response(
                {"message": "File is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        extension = None

        content_type = file.content_type

        if content_type == "image/jpeg":
            extension = "jpg"
        elif content_type == "image/png":
            extension = "png"
        elif content_type == "image/gif":
            extension = "gif"
        else:
            extension = "unknown"
        try:
            timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
            stored_url = upload_to_azure_blob(
                file,
                f"profile-pics/{remove_spaces_from_text(user.client.organization.name)}",
                f"{user.id}_{timestamp}.{extension}",
            )
            user.photo = stored_url
            user.save()
            return Response(
                {"message": "Profile picture uploaded successfully"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            return Response(
                {"message": "Something went wrong"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def delete(self, request):
        user = request.user
        try:
            user.photo = None
            user.save()
            return Response(
                {"message": "Profile picture deleted successfully"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            return Response(
                {"message": "Something went wrong"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class OnboardingView(CustomAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, type):
        data = request.data
        company = data.get("company")
        organization = Organization.objects.filter(name=company).first()
        user = request.user
        if not organization:
            return Response(
                {"message": "Organization doesn't exist"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if type.lower() == "client":
            first_name = data.get("first_name")
            last_name = data.get("last_name")
            email = data.get("email")

            department = data.get("department")
            job_title = data.get("job_title")

            user = User.objects.filter(email=email).first()
            if not user:
                return Response(
                    {"message": "User doesn't exist"}, status=status.HTTP_404_NOT_FOUND
                )

            try:
                user.first_name = first_name
                user.last_name = last_name
                user.save()
            except Exception as e:
                logger.error(f"Error: {e}")
                return Response(
                    {"message": "Something went wrong"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            client = Client.objects.filter(user=user).first()

            if not client:
                return Response(
                    {"message": "Client doesn't exist"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            try:
                client.department = department
                client.job_title = job_title
                client.save()
            except Exception as e:
                logger.error(f"Error: {e}")
                return Response(
                    {"message": "Something went wrong"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response(status=status.HTTP_200_OK)
        elif type == "team_office_hours":

            # office hourse schema
            # "office_hours": [
            #     {
            #         "weekday": "Monday",
            #         "is_open": true,
            #         "open_time": "09:00",
            #         "close_time": "18:00"
            #     }, ...]

            company = data.get("company")
            office_hours = data.get("office_hours")
            team_name = data.get("team_name")
            timezone = data.get("timezone")
            try:
                organization.team_name = team_name
                organization.timezone = timezone
                organization.save()
                # delete the office hours
                OfficeHours.objects.filter(organization=organization).delete()

                for day_data in office_hours:
                    serializer = OfficeHoursSerializer(data=day_data)
                    if serializer.is_valid():
                        # Check if the instance exists, update or create accordingly
                        instance, _ = OfficeHours.objects.update_or_create(
                            organization=organization,
                            weekday=day_data["weekday"],
                            defaults=serializer.validated_data,
                        )
                    else:
                        # If the data is not valid, return an error response
                        return Response(
                            serializer.errors, status=status.HTTP_400_BAD_REQUEST
                        )

            except Exception as e:
                logger.error(f"Error: {e}")
                return Response(
                    {"message": "Something went wrong"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response({"message": "office hours set"}, status=status.HTTP_200_OK)
        elif type == "widget":
            widgetObj = Widget.objects.filter(organization=organization).first()
            if widgetObj:
                widgetObj.avatar = data.get("avatar")
                widgetObj.position = data.get("position")
                widgetObj.is_active = data.get("is_active", True)
                widgetObj.save()
                return Response(
                    {"message": "Widget updated"}, status=status.HTTP_200_OK
                )

            serializer = WidgetSerializer(data=data)
            if serializer.is_valid():
                serializer.save(organization=organization)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        elif type == "welcome_note":
            welcome_note_id = data.get("welcome_note_id")
            try:
                welcome_note = WelcomeNote.objects.filter(id=welcome_note_id).first()
                if not welcome_note:
                    return Response(
                        {"message": "Welcome note not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                organization.welcome_note = welcome_note
                organization.save()
            except Exception as e:
                logger.error(f"Error: {e}")
                return Response(
                    {"message": "Something went wrong"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            return Response({"message": "Welcome note set"}, status=status.HTTP_200_OK)
        elif type == "call_you_back_note":
            call_you_back_note_id = data.get("call_you_back_note_id")
            try:
                call_you_back_note = CallYouBackNote.objects.filter(
                    id=call_you_back_note_id
                ).first()
                if not call_you_back_note:
                    return Response(
                        {"message": "Call you back note not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                organization.call_you_back_note = call_you_back_note
                organization.save()
            except Exception as e:
                logger.error(f"Error: {e}")
                return Response(
                    {"message": "Something went wrong"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            return Response(
                {"message": "Call you back note set"}, status=status.HTTP_200_OK
            )
        elif type == "out_of_office_note":
            out_of_office_note_id = data.get("out_of_office_note_id")
            try:
                out_of_office_note = OutOfOfficeNote.objects.filter(
                    id=out_of_office_note_id
                ).first()
                if not out_of_office_note:
                    return Response(
                        {"message": "Out of office note not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                organization.out_of_office_note = out_of_office_note
                organization.save()
            except Exception as e:
                logger.error(f"Error: {e}")
                return Response(
                    {"message": "Something went wrong"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            return Response(
                {"message": "Out of office note set"}, status=status.HTTP_200_OK
            )
        elif type == "auto_send_welcome_note":
            auto_send_welcome_note = data.get("auto_send_welcome_note")
            try:
                if auto_send_welcome_note == True:
                    automatically_sent_after = data.get("automatically_sent_after")
                    organization.auto_sent_after = automatically_sent_after
                organization.auto_send_welcome_note = auto_send_welcome_note
                organization.save()
            except Exception as e:
                logger.error(f"Error: {e}")
                return Response(
                    {"message": "Something went wrong"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            return Response(
                {"message": "Auto send welcome note set"}, status=status.HTTP_200_OK
            )
        elif type == "onboarded_by":
            try:
                client = user.client
                if not organization.onboarded_by:
                    organization.onboarded_by = client
                    organization.save()
                    return Response(
                        {"message": "Set onboarded_by done"}, status=status.HTTP_200_OK
                    )
                else:
                    return Response(
                        {"message": "Onboarded by already set"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except Exception as e:
                logger.error(f"Error: {e}")
                return Response(
                    {"message": "Something went wrong"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        elif type == "share_code_instructions":
            email = data.get("email")

            message = f"Your colleague, {user.first_name + ' ' + user.last_name}, has signed up for PingBase. The final step requires your help."
            sub_message = f"PingBase is a launcher that sits within your product, similar to a chatbot launcher. To go live, please drop the 2 snippets of code below into your product. Check out our <a href='https://docs.pingbase.ai/'>developer docs<a> for further assistance."
            html_email_body = (
                f"Hi there,<br><br>"
                f"{message}<br><br>"
                f"{sub_message}<br><br>"
                f"{get_integration_code_snippet(organization.token)} <br><br>"
                f"If you have any questions, just hit reply."
                f"<br><br>Thanks,<br>Team PingBase<br>"
            )
            # email_body = "Hi " + user.email + message + verification_link
            data = {
                "html_email_body": html_email_body,
                "to_email": email,
                "email_subject": "You've been invited to setup PingBase",
                "email_body": None,
            }
            try:
                Mail.send_code_email(data)

            except Exception as e:
                logger.error(f"Error while sending code snippet: {e}")

            return Response(
                {"message": "Code instructions shared successfully!"},
                status=status.HTTP_200_OK,
            )
        elif type == "integration_status":
            endUsersCount = EndUser.objects.filter(organization=organization).count()
            client = user.client
            if endUsersCount > 0:
                organization.onboarded = True
                organization.save()
                client.onboarded = True
                client.save()
                return Response(
                    {"message": "Integration Done"}, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"message": "Integration not done"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        elif type == "check_in_feature":
            checkInFeatureObj = CheckInFeature.objects.filter(
                organization=organization
            ).first()
            if checkInFeatureObj:
                checkInFeatureObj.master_switch = data.get("master_switch")
                checkInFeatureObj.skip_switch = data.get("skip_switch", False)
                checkInFeatureObj.support_email = data.get("support_email")
                checkInFeatureObj.save()
                return Response(
                    {"message": "CheckIn feature updated"}, status=status.HTTP_200_OK
                )

            serializer = CheckInFeatureSerializer(data=data)
            if serializer.is_valid():
                serializer.save(organization=organization)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(
                {"message": "Invalid onboarding type"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def put(self, request, type):
        user = request.user
        data = request.data
        company = data.get("company")
        organization = Organization.objects.filter(name=company).first()

        if not organization:
            return Response(
                {"message": "Organization doesn't exist"},
                status=status.HTTP_404_NOT_FOUND,
            )

        client = Client.objects.filter(user=user).first()
        try:
            if type == "organization_onboarding":
                organization.onboarded = True
                organization.onboarded_by = client
                organization.save()

            elif type == "client_onboarding":
                client.onboarded = True
                client.save()
        except Exception as e:
            logger.error(f"Error: {e}")
            return Response(
                {"message": "Something went wrong"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(status=status.HTTP_200_OK)


class OnboardingDataView(CustomGenericAPIListView):
    def get(self, request, type):
        try:
            if type == "welcome_note":
                queryset = WelcomeNote.objects.all()
                serializer = WelcomeNoteSerializer(queryset, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            elif type == "call_you_back_note":
                queryset = CallYouBackNote.objects.all()
                serializer = CallYouBackNoteSerializer(queryset, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            elif type == "out_of_office_note":
                queryset = OutOfOfficeNote.objects.all()
                serializer = OutOfOfficeNoteSerializer(queryset, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"message": "Invalid onboarding type"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            logger.error(f"Error: {e}")
            return Response(
                {"message": "Something went wrong"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CreateEndUserView(CustomGenericAPIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        org_token = request.headers.get("organization-token")
        if not org_token:
            return Response(
                {"message": "Organization token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        organization = Organization.objects.filter(token=org_token).first()
        if not organization:
            return Response(
                {"message": "Organization not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        user = User.objects.filter(phone=request.data.get("phone")).first()

        # end_user = EndUser.objects.filter(email=request.data.get("email")).first()

        is_new = request.data.get("is_new", False)
        if user:
            current_timestamp = timezone.now()
            end_user_meetings = Meeting.objects.filter(
                organizer=user, start_time__gte=current_timestamp
            )
            sessions = EndUserSession.objects.filter(
                end_user=user.end_user, organization=organization
            ).count()
            endUser = user.end_user

            try:
                endUser.first_name = request.data.get("first_name", None)
                endUser.last_name = request.data.get("last_name", None)
                endUser.role = request.data.get("role", None)
                endUser.trial_type = request.data.get("trial_type", None)
                endUser.company = request.data.get("company", None)
                endUser.user.email = request.data.get("email", None)
                endUser.is_new = is_new
                endUser.save()
                endUser.user.save()
            except Exception as e:
                logger.error(f"Error while updating endUser details: {e}")

            return Response(
                {
                    "id": user.id,
                    "message": "EndUser already exists",
                    "sessions": sessions,
                    "is_new": endUser.is_new,
                    "check_in_status": endUser.check_in_status,
                    "end_user_meetings": end_user_meetings.count(),
                },
                status=status.HTTP_200_OK,
            )
        required_data = {
            "organization_name": organization.name,
            "first_name": request.data.get("first_name", None),
            "last_name": request.data.get("last_name", None),
            "email": request.data.get("email", None),
            "role": request.data.get("role", None),
            "trial_type": request.data.get("trial_type", None),
            "company": request.data.get("company", None),
            "is_new": request.data.get("is_new", None),
            "phone": request.data.get("phone", None),
        }
        serializer = EndUserSerializer(data=required_data)
        if serializer.is_valid():
            end_user = serializer.save()
            # Create a new EndUserLogin instance
            async_id = EndUserSession.create_session_async(end_user, organization)
            return Response(
                {
                    "message": "EndUser created successfully.",
                    "id": end_user.user.id,
                    "sessions": 1,
                    "is_new": end_user.is_new,
                    "check_in_status": end_user.check_in_status,
                    "end_user_meetings": 0,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InitEndUserView(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request, *args, **kwargs):
        org_token = request.headers.get("organization-token")
        if not org_token:
            return Response(
                {"message": "Organization token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        organization = Organization.objects.filter(token=org_token).first()
        if not organization:
            return Response(
                {"message": "Organization token not valid"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            orgName = organization.name
            orgWidget = organization.widgets

            widgetIsActive = orgWidget.is_active
            widgetPosition = orgWidget.position
            widgetAvatar = orgWidget.avatar
            widgetAvatarColor1 = orgWidget.color_1
            widgetAvatarColor2 = orgWidget.color_2

            widgetAvatarNumber = int("".join(filter(str.isdigit, widgetAvatar)))

            teamName = organization.team_name
            return Response(
                {
                    "organization": orgName,
                    "widget": {
                        "is_active": widgetIsActive,
                        "position": widgetPosition,
                        "avatar": widgetAvatarNumber,
                        "color_1": widgetAvatarColor1,
                        "color_2": widgetAvatarColor2,
                    },
                    "team_name": teamName,
                    "features": FeatureFlagConnectSerializer(
                        organization.feature_flags_connect.all(), many=True
                    ).data,
                    "check_in_feature": (
                        CheckInFeatureSerializer(organization.check_in_feature).data
                        if hasattr(organization, "check_in_feature")
                        else None
                    ),
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            return Response(
                {"message": "Something went wrong"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def put(self, request, *args, **kwargs):
        org_token = request.headers.get("organization-token")
        if not org_token:
            return Response(
                {"message": "Organization token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        organization = Organization.objects.filter(token=org_token).first()
        if not organization:
            return Response(
                {"message": "Organization token not valid"},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = request.data
        new_check_in_status = data.get("check_in_status")
        user_id = data.get("user_id")
        user = None
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"message": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )
        endUser = user.end_user

        current_check_status = endUser.check_in_status

        if current_check_status in [SKIPPED, NOT_APPLICABLE, COMPLETED]:
            return Response(
                {"message": "Check-in status already set"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            endUser.check_in_status = new_check_in_status
            endUser.save()

            # create a new Event
            # Create an Event for the check-in status change
            event_type = None
            if new_check_in_status == COMPLETED:
                event_type = CHECKIN_COMPLETED
            elif new_check_in_status == SKIPPED:
                event_type = CHECKIN_SKIPPED
            else:
                event_type = CHECKIN_NOT_APPLICABLE

            event = Event.create_event(
                event_type=event_type,
                source_user_id=int(user_id),
                destination_user_id=None,
                status=SUCCESS,
                duration=0,
                frontend_screen="NA",
                agent_name=None,
                initiated_by=MANUAL,
                interaction_type=NOT_APPLICABLE,
                interaction_id=None,
                is_parent=False,
                storage_url=None,
                organization=organization,
                request_meta=None,
                error_stack_trace=None,
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            return Response(
                {"message": "Something went wrong"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(
            {"message": "Check-in status updated successfully"},
            status=status.HTTP_200_OK,
        )


class ExitEndUserView(CustomGenericAPIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        endUserId = request.query_params.get("endUserId", None)
        try:
            endUser = User.objects.filter(id=endUserId).first().end_user
            endUserSessionEvent = (
                EndUserSession.objects.filter(end_user=endUser)
                .order_by("-modified_at")
                .first()
            )
            if endUserSessionEvent:
                endUserSessionEvent.last_session_active = timezone.now()
                endUserSessionEvent.save()
        except Exception as e:
            logger.error(f"Error: {e}")
            return Response(
                {"message": "EndUser does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {"message": "EndUser exit event recorded"},
            status=status.HTTP_200_OK,
        )


class EndUserSessionView(CustomGenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        client = request.user
        enduser_id = request.query_params.get("enduser_id", None)
        session_id = request.query_params.get("session_id", None)

        try:
            if session_id:
                try:
                    session_obj = UserSession.objects.get(session_id=session_id)
                    return Response(
                        {
                            "session_id": session_obj.session_id,
                            "initial_events": session_obj.initial_events,
                            "created_at": session_obj.created_at,
                            "modified_at": session_obj.modified_at,
                            "storage_url": session_obj.storage_url,
                        },
                        status=status.HTTP_200_OK,
                    )
                except Exception as e:
                    logger.error(f"Error: {e}")
                    return Response(
                        {"message": "Session not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            user = User.objects.get(id=enduser_id)
            session_obj = (
                UserSession.objects.filter(user=user).order_by("-modified_at").first()
            )
            if session_obj:
                return Response(
                    {
                        "session_id": session_obj.session_id,
                        "initial_events": session_obj.initial_events,
                        "created_at": session_obj.created_at,
                        "modified_at": session_obj.modified_at,
                        "storage_url": session_obj.storage_url,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"message": "Session not found"}, status=status.HTTP_404_NOT_FOUND
                )
        except User.DoesNotExist:
            return Response(
                {"message": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


class ClientView(CustomGenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        user = request.user
        data = request.data
        client = user.client

        active = data.get("active", False)
        scheduled_time = data.get("scheduled_time", None)

        try:
            client.is_client_online = active
            client.save()
        except Exception as e:
            logger.error(f"Error: {e}")

        if scheduled_time:
            scheduled_time = datetime.datetime.fromisoformat(scheduled_time)
            try:
                schedule_active_status_for_client(client, active, scheduled_time)
            except Exception as e:
                logger.error(f"Error: {e}")

        return Response(
            {"message": "Client status updated successfully"},
            status=status.HTTP_200_OK,
        )


class TeamRegistrationView(generics.GenericAPIView):

    def post(self, request):
        # Your code for team registration goes here
        data = request.data

        team_name = data.get("team_name")
        office_hours = data.get("office_hours")
        email = data.get("email")

        user = User.objects.filter(email=email).first()

        if not user or not user.is_verified or user.is_active == False:
            return Response(status=status.HTTP_404_NOT_FOUND)

        client = Client.objects.filter(user__email=email).first()
        if client:
            client.team_name = team_name
            client.save()

            organization = Organization.objects.filter(
                name=client.organization.name
            ).first()
            if organization:
                organization.office_hours = office_hours
                organization.save()

        # return 200 status code
        return Response(
            {"message": "Team registered successfully"}, status=status.HTTP_200_OK
        )


class RegistrationView(generics.GenericAPIView):

    serializer_class = RegistrationSerializer

    def post(self, request):
        try:
            user = request.data

            job_title = user.get("job_title")
            department = user.get("department")
            company = user.get("company", "").lower()
            role = user.get("role", "standard_user")

            organization = Organization.objects.filter(name=company).first()

            if not organization:
                organization = Organization.objects.create(name=company)
                organization.save()

                pusher_channel_app = PusherChannelApp.objects.filter(
                    organization=organization
                ).first()

                if not pusher_channel_app:
                    # get a random pusher_channel_app_object
                    pusher_channel_app = PusherChannelApp.objects.filter(
                        organization__isnull=True
                    ).first()
                    pusher_channel_app.organization = organization
                    pusher_channel_app.save()

            serializer = self.serializer_class(data=user)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            user_data = serializer.data

            ####  Sending email
            user = User.objects.get(email=user_data["email"])

            token = RefreshToken.for_user(user).access_token

            current_site_domain = get_current_site(request).domain
            relativeLink = reverse("verify-email")

            verification_link = (
                "https://" + current_site_domain + relativeLink + "?token=" + str(token)
            )
            message = ". Ready to serve? Use the link below to verify your email and secure your spot in the Pingbase arena. \nIf you received this by a wild shot and weren’t expecting any account verification email, feel free to ignore this volley. \n"
            email_body = "Hi " + user.email + message + verification_link
            data = {
                "email_body": email_body,
                "to_email": user.email,
                "email_subject": "Verify your email",
            }
            Mail.send_email(data)

            client = Client.objects.filter(user=user).first()

            if not client:
                client = Client.objects.create(
                    user=user,
                    job_title=job_title,
                    department=department,
                    organization=organization,
                    role=role,
                )
                client.save()

            return Response(user_data, status=status.HTTP_201_CREATED)
        except User.DoesNotExist:
            # return 404 status code to indicate that the user does not exist
            return Response(status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Error: {e}")
            # return 500 status code to indicate that an error occurred
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmailVerificationView(CustomAPIView):
    serializer_class = EmailVerificationSerializer

    def get(self, request):
        token = request.GET.get("token")
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user = User.objects.get(id=payload["user_id"])

            client = Client.objects.filter(user=user).first()
            organization = client.organization

            # check if the user is the first user of the company
            all_clients_objects_count = Client.objects.filter(
                organization=organization
            ).count()

            company_name = client.organization.name

            if not user.is_verified:
                user.is_verified = True
                user.is_active = True
                user.save()

            base_url = "https://toolsvilla.app.pingbase.ai/signup"
            base_url_2 = "https://toolsvilla.app.pingbase.ai"
            query_params = f"?email={user.email}&company_name={company_name}"
            redirect_url = base_url + query_params
            if all_clients_objects_count == 1:
                redirect_url = base_url_2
            return redirect(redirect_url)

        except jwt.ExpiredSignatureError as identifier:
            return Response(
                {"error": "Activation Expired"}, status=status.HTTP_400_BAD_REQUEST
            )
        except jwt.exceptions.DecodeError as identifier:
            return Response(
                {"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST
            )


class ResendVerificationEmailView(CustomAPIView):
    serializer_class = ResendVerificationEmailSerializer

    def post(self, request):
        input = request.data
        Email = input["email"]

        try:
            if User.objects.filter(email=Email).exists:
                user = User.objects.get(email__exact=Email)
                token = RefreshToken.for_user(user).access_token
                current_site_domain = get_current_site(request).domain
                relativeLink = reverse("verify-email")
                verification_link = (
                    "https://"
                    + current_site_domain
                    + relativeLink
                    + "?token="
                    + str(token)
                )
                message = ". Ready to serve? Use the link below to verify your email and secure your spot in the Pingbase arena. \nIf you received this by a wild shot and weren’t expecting any account verification email, feel free to ignore this volley. \n"
                email_body = "Hi " + Email + message + verification_link
                data = {
                    "email_body": email_body,
                    "to_email": Email,
                    "email_subject": "Verify your email",
                }
                Mail.send_email(data)
                return Response(
                    {"Verification Email sent. Check your inbox."},
                    status=status.HTTP_200_OK,
                )

        except User.DoesNotExist as exc:
            return Response(
                {"The email address does not not match any user account."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class LoginView(CustomGenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        print("data", serializer.data)

        return Response(serializer.data, status=status.HTTP_200_OK)


class RequestPasswordResetEmailView(CustomGenericAPIView):
    serializer_class = RequestPasswordResetEmailSerializer

    def post(self, request):

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        Email = request.data["email"]

        if User.objects.filter(email=Email).exists():
            user = User.objects.get(email=Email)
            uidb64 = urlsafe_base64_encode(smart_bytes(user.id))
            token = PasswordResetTokenGenerator().make_token(user)

            current_site = get_current_site(request=request).domain
            relativeLink = reverse(
                "password-reset-confirm", kwargs={"uidb64": uidb64, "token": token}
            )
            absurl = "https://" + current_site + relativeLink

            html_email_body = (
                f"Hello! \n" f"<a href='{absurl}'>Click Here To Reset Password</a> \n"
            )
            data = {
                "html_email_body": html_email_body,
                "email_body": None,
                "to_email": user.email,
                "email_subject": "Reset your password",
            }

            logger.info(f"data: {data}")

            Mail.send_email(data)
        else:
            return Response(
                {"Error": "The email address does not not match any user account."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"Success": "Password reset email sent"}, status=status.HTTP_200_OK
        )


class PasswordResetTokenValidationView(CustomGenericAPIView):
    def get(self, request, uidb64, token):

        try:
            id = smart_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(id=id)

            if not PasswordResetTokenGenerator().check_token(user, token):
                return Response(
                    {
                        "Error": "Password reset link is expired! Please request for a new one!"
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            # Redirect to frontend
            base_url = "https://toolsvilla.app.pingbase.ai/update-password"
            query_params = f"?uidb64={uidb64}&token={token}&email={user.email}"
            redirect_url = base_url + query_params

            return redirect(redirect_url)

        except DjangoUnicodeDecodeError as exc:
            if not PasswordResetTokenGenerator().check_token(user):
                return Response(
                    {"Error": "Token is not valid! Please request for a new one!"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )


class SetNewPasswordView(CustomGenericAPIView):
    serializer_class = SetNewPasswordSerializer

    def put(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            {"success": True, "message": "Password changed successfully"},
            status=status.HTTP_200_OK,
        )


class ResetPasswordAdhocView(CustomGenericAPIView):
    serializer_class = SetNewPasswordAdhocSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        user = request.user

        context = {"user": user}
        logger.info(f"user_id -- { user.id}")
        serializer = self.serializer_class(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        return Response(
            {"success": True, "message": "Password changed successfully"},
            status=status.HTTP_200_OK,
        )


class EndUserList(CustomGenericAPIListView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = CustomEndUserSerializer

    def get(self, request, *args, **kwargs):
        user = request.user

        client = user.client
        query = request.query_params.get("search", None)

        if not client:
            return Response(
                {"message": "Client doesn't exist"},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            if query:
                search = query.lower()
                filtered_users_ids = User.objects.filter(
                    Q(phone__icontains=search)
                    | Q(email__icontains=search)
                    | Q(first_name__icontains=search)
                    | Q(last_name__icontains=search)
                    | Q(end_user__company__icontains=search)
                ).values_list("id", flat=True)

                end_users = client.organization.end_users.filter(
                    user__id__in=filtered_users_ids
                )

            else:
                end_users = client.organization.end_users.all()

            serializer = self.serializer_class(end_users, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error: {e}")
            return Response(
                {"message": "Something went wrong"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def put(self, request, *args, **kwargs):
        user = request.user
        data = request.data
        end_user_id = data.get("end_user_id")

        check_in_status = data.get("check_in_status")
        try:
            end_user = User.objects.get(id=end_user_id).end_user
        except User.DoesNotExist as e:
            logger.error(f"Error: {e}")
            return Response(
                {"message": "EndUser doesn't exist"},
                status=status.HTTP_404_NOT_FOUND,
            )
        client = user.client
        # check if the client organization is the same as the end_user organization
        if client.organization != end_user.organization:
            return Response({"message": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        is_request_valid = validate_check_in_status(
            check_in_status, end_user.check_in_status
        )
        if is_request_valid:
            end_user.check_in_status = check_in_status
            end_user.save()

            # Create an Event
            # Create an Event for the check-in status change
            event_type = None
            if check_in_status == COMPLETED:
                event_type = CHECKIN_COMPLETED
            elif check_in_status == SKIPPED:
                event_type = CHECKIN_SKIPPED
            else:
                event_type = CHECKIN_NOT_APPLICABLE

            event = Event.create_event(
                event_type=event_type,
                source_user_id=user.id,
                destination_user_id=int(end_user_id),
                status=SUCCESS,
                duration=0,
                frontend_screen="NA",
                agent_name=None,
                initiated_by=MANUAL,
                interaction_type=NOT_APPLICABLE,
                interaction_id=None,
                is_parent=True,
                storage_url=None,
                organization=client.organization,
                request_meta=None,
                error_stack_trace=None,
            )
            return Response(
                {"message": "Check in status updated successfully"},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"message": "Invalid check in status"},
            status=status.HTTP_400_BAD_REQUEST,
        )


class UserList(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class UserDetail(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class LogoutView(CustomGenericAPIView):
    serializer_class = LogoutSerializer

    # permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"success": True, "message": "Logged out successfully"},
            status=status.HTTP_200_OK,
        )
