from .serializers import (
    RegistrationSerializer,
    EmailVerificationSerializer,
    ResendVerificationEmailSerializer,
    LoginSerializer,
    RequestPasswordResetEmailSerializer,
    SetNewPasswordSerializer,
    UserSerializer,
    LogoutSerializer,
)
from rest_framework.response import Response
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth import get_user_model
from django.urls import reverse
from .utils import Mail
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import generics, status, views, permissions
from django.conf import settings
import jwt
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import smart_bytes, smart_str, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse
from .models import (
    Organization,
    Client,
    OfficeHours,
    WelcomeNote,
    CallYouBackNote,
    OutOfOfficeNote,
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
)
from infra_utils.views import (
    CustomAPIView,
    CustomGenericAPIView,
    CustomGenericAPIListView,
)
from infra_utils.utils import password_rule_check, generate_strong_password

User = get_user_model()

import logging

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
                    client = Client.objects.filter(user=user).first()
                    if client:
                        return Response(
                            {"message": "Client already exists."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                # first create an organization with company name
                # check if the organization exists already
                organization = Organization.objects.filter(name=company).first()

                if not organization:
                    organization = Organization.objects.create(name=company)
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
                message = ". Use the link below to verify your email.\n If you were not expecting any account verification email, please ignore this \n"
                email_body = "Hi " + user.email + message + verification_link
                data = {
                    "email_body": email_body,
                    "to_email": user.email,
                    "email_subject": "Demo Email Verification",
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

                return Response(user_data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response(
                    {"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )


class InviteTeamateView(CustomGenericAPIView):

    serializer_class = RegistrationSerializer

    def post(self, request, type, *args, **kwargs):
        data = request.data
        email = data.get("email")
        company = data.get("company")
        invitee_email = data.get("invitee_email")

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

        ####  Sending email
        user = User.objects.get(email=user_data["email"])

        token = RefreshToken.for_user(user).access_token

        current_site_domain = get_current_site(request).domain
        relativeLink = reverse("verify-email")

        verification_link = (
            "https://" + current_site_domain + relativeLink + "?token=" + str(token)
        )
        message = ". Your teamate invited you to join Pingbase Yay! \nUse the link below to verify your email.\n If you were not expecting any account verification email, please ignore this \n"
        email_body = "Hi " + user.email + message + verification_link
        data = {
            "email_body": email_body,
            "to_email": user.email,
            "email_subject": "Demo Email Verification",
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

        return Response(user_data, status=status.HTTP_201_CREATED)


class ProfileView(CustomGenericAPIView):
    is_authenticated = True

    def get(self, request, type):
        user = request.user
        if type == "client":
            client = Client.objects.filter(user=user).first()
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


class OnboardingView(CustomAPIView):
    def post(self, request, type):
        data = request.data
        company = data.get("company")
        organization = Organization.objects.filter(name=company).first()
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
            try:
                organization.team_name = team_name
                organization.save()
                # delete the office hours
                OfficeHours.objects.filter(organization=organization).delete()

                for day_data in office_hours:
                    serializer = OfficeHoursSerializer(data=day_data)
                    if serializer.is_valid():
                        # Check if the instance exists, update or create accordingly
                        instance, _ = OfficeHours.objects.update_or_create(
                            organization=organization,
                            day=day_data["weekday"],
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
            serializer = WidgetSerializer(data)
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
        else:
            return Response(
                {"message": "Invalid onboarding type"},
                status=status.HTTP_400_BAD_REQUEST,
            )


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


class CreateEndUserView(generics.GenericAPIView):
    def post(self, request, *args, **kwargs):
        serializer = EndUserSerializer(data=request.data)
        if serializer.is_valid():
            end_user = serializer.save()
            return Response(
                {
                    "message": "EndUser created successfully.",
                    "end_user_id": end_user.id,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
            message = ". Use the link below to verify your email.\n If you were not expecting any account verification email, please ignore this \n"
            email_body = "Hi " + user.email + message + verification_link
            data = {
                "email_body": email_body,
                "to_email": user.email,
                "email_subject": "Demo Email Verification",
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

            if not user.is_verified:
                user.is_verified = True
                user.is_active = True
                user.save()
            return Response({"Email Successfully verified"}, status=status.HTTP_200_OK)

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
                message = ". Use the link below to verify your email.\n If you were not expecting any account verification email, please ignore this \n"
                email_body = "Hi " + Email + message + verification_link
                data = {
                    "email_body": email_body,
                    "to_email": Email,
                    "email_subject": "Demo Email Verification",
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

        return Response(serializer.data, status=status.HTTP_200_OK)


class RequestPasswordResetEmailView(CustomGenericAPIView):
    serializer_class = RequestPasswordResetEmailSerializer

    def post(self, request):
        password = request.data["password"]
        if not password_rule_check(password):
            return Response(
                {
                    "message": "Password must contain at least 8 characters, at least one uppercase letter, one lowercase letter, one number and one special character",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
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

            email_body = (
                "Hello! \n Use the link below to reset your password \n" + absurl
            )
            data = {
                "email_body": email_body,
                "to_email": user.email,
                "email_subject": "Reset your password",
            }

            Mail.send_email(data)

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

            return Response(
                {
                    "Success": True,
                    "Message": "Valid Credentials",
                    "uidb64": uidb64,
                    "token": token,
                },
                status=status.HTTP_200_OK,
            )

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
