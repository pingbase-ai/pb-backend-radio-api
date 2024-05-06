from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib import auth
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from infra_utils.utils import password_rule_check
from home.models import EndUserSession
from .models import (
    EndUser,
    OfficeHours,
    Widget,
    WelcomeNote,
    CallYouBackNote,
    OutOfOfficeNote,
    Client,
    Organization,
    FeatureFlagConnect,
)
import datetime
import logging

# from .models import Customer


User = get_user_model()
logger = logging.getLogger("django")


class CustomEndUserSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    last_login = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()
    sessions = serializers.SerializerMethodField()
    trial_type = serializers.SerializerMethodField()
    linkedin = serializers.SerializerMethodField()
    last_session_login = serializers.SerializerMethodField()

    def get_id(self, obj):
        return obj.user.id

    def get_first_name(self, obj):
        return obj.user.first_name

    def get_last_name(self, obj):
        return obj.user.last_name

    def get_is_online(self, obj):
        return obj.user.is_online

    def get_last_login(self, obj):
        return obj.user.last_login

    def get_role(self, obj):
        return obj.role

    def get_email(self, obj):
        return obj.user.email

    def get_company(self, obj):
        return obj.company

    def get_sessions(self, obj):
        total_sessions = EndUserSession.objects.filter(end_user=obj).count()
        return total_sessions

    def get_trial_type(self, obj):
        return obj.trial_type

    def get_linkedin(self, obj):

        return obj.linkedin

    def get_last_session_login(self, obj):
        try:
            last_session = (
                EndUserSession.objects.filter(end_user=obj)
                .order_by("-modified_at")
                .first()
            )
            if last_session:
                return last_session.last_session_active
            return None
        except Exception as e:
            logger.error(f"Error while fetching last session login: {e}")
            return None

    class Meta:
        model = EndUser
        fields = [
            "id",
            "first_name",
            "last_name",
            "is_online",
            "last_login",
            "role",
            "email",
            "company",
            "sessions",
            "trial_type",
            "linkedin",
            "last_session_login",
        ]


class EndUserSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    organization_name = serializers.CharField(
        write_only=True,
    )
    role = serializers.CharField(write_only=True)
    trial_type = serializers.CharField(write_only=True)
    company = serializers.CharField(write_only=True)

    class Meta:
        model = EndUser
        fields = [
            "first_name",
            "last_name",
            "email",
            "organization_name",
            "role",
            "trial_type",
            "company",
        ]

    def create(self, validated_data):
        print(validated_data)
        return EndUser.objects.create_enduser(**validated_data)


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(max_length=68, min_length=8, write_only=True)

    class Meta:
        model = User
        fields = ["email", "password"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


# class CustomerRegistrationSerializer(serializers.ModelSerializer):
#     password = serializers.CharField(max_length=68, min_length=8, write_only=True)

#     class Meta:
#         model = Customer
#         fields = ["first_name", "last_name", "email", "password", "company"]

#     def create(self, validated_data):
#         return User.objects.create_user(**validated_data)


class EmailVerificationSerializer(serializers.ModelSerializer):
    token = serializers.CharField(max_length=555)

    class Meta:
        model = User
        fields = ["token"]


class ResendVerificationEmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email"]


class LoginSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=255, min_length=3)
    password = serializers.CharField(max_length=68, min_length=8, write_only=True)
    access_token = serializers.CharField(min_length=8, read_only=True)
    refresh_token = serializers.CharField(min_length=8, read_only=True)

    class Meta:
        model = User
        fields = ["email", "password", "access_token", "refresh_token"]

    def validate(self, attrs):
        email = attrs.get("email", "")
        password = attrs.get("password", "")

        user = auth.authenticate(email=email, password=password)

        if not user:
            raise AuthenticationFailed("Invalid Login Credentials, try again!")
        if not user.is_active:
            raise AuthenticationFailed(
                "Your Acccount is disabled, please contact admin"
            )
        # User should still be able to login without verifying email
        # if not user.is_verified:
        #     raise AuthenticationFailed("Your Email is not verified")

        tokens = user.get_tokens()

        access_token = tokens["access"]
        refresh_token = tokens["refresh"]

        user.last_login = datetime.datetime.now()
        user.save()

        return {
            "email": user.email,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }


class RequestPasswordResetEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class SetNewPasswordAdhocSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, attrs):

        try:
            password = attrs.get("password")

            is_valid = password_rule_check(password)

            if not is_valid:
                raise ValidationError(
                    "Password must contain at least 8 characters, 1 uppercase, 1 lowercase, 1 number and 1 special character"
                )

            user = self.context.get("user")
            user.set_password(password)
            user.save()
            return super().validate(attrs)
        except Exception as e:
            raise ValidationError("Something went wrong", 401)


class SetNewPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=8, write_only=True)
    token = serializers.CharField(write_only=True)
    uidb64 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        try:
            password = attrs.get("password")
            token = attrs.get("token")
            uidb64 = attrs.get("uidb64")

            id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(id=id)

            if not PasswordResetTokenGenerator().check_token(user, token):
                raise AuthenticationFailed("The reset link is invalid or expired.", 401)
            user.set_password(password)
            user.save()

        except Exception as e:
            raise AuthenticationFailed("The reset link is invalid or expired.", 401)
        return super().validate(attrs)


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "is_online",
            "last_login",
            "photo",
        ]


class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs["refresh_token"]
        return attrs

    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()
        except TokenError:
            raise ValidationError(
                {"incorrect_token": "The token is either invalid or expired"}
            )


class OfficeHoursSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfficeHours
        fields = ["weekday", "is_open", "open_time", "close_time"]


class WidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Widget
        fields = ["avatar", "position", "is_active"]


class WelcomeNoteSerializer(serializers.ModelSerializer):
    play_time = serializers.DurationField()

    class Meta:
        model = WelcomeNote
        fields = ["id", "title", "description", "is_active", "storage_url", "play_time"]


class CallYouBackNoteSerializer(serializers.ModelSerializer):
    play_time = serializers.DurationField()

    class Meta:
        model = CallYouBackNote
        fields = ["id", "title", "description", "is_active", "storage_url", "play_time"]


class OutOfOfficeNoteSerializer(serializers.ModelSerializer):
    play_time = serializers.DurationField()

    class Meta:
        model = OutOfOfficeNote
        fields = ["id", "title", "description", "is_active", "storage_url", "play_time"]


class OrganizationSerializerCustom(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    token = serializers.SerializerMethodField()
    website = serializers.SerializerMethodField()
    team_name = serializers.SerializerMethodField()
    onboarded = serializers.SerializerMethodField()
    widget = serializers.SerializerMethodField()
    welcomeNote = serializers.SerializerMethodField()
    callYouBackNote = serializers.SerializerMethodField()
    outOfOfficeNote = serializers.SerializerMethodField()
    officeHours = serializers.SerializerMethodField()
    timezone = serializers.SerializerMethodField()
    auto_send_welcome_note = serializers.SerializerMethodField()
    onboarded = serializers.SerializerMethodField()
    onboarded_by = serializers.SerializerMethodField()
    auto_sent_after = serializers.SerializerMethodField()

    def get_name(self, obj):
        return obj.name

    def get_token(self, obj):
        return obj.token

    def get_website(self, obj):
        return obj.website

    def get_team_name(self, obj):
        return obj.team_name

    def get_onboarded(self, obj):
        return obj.onboarded

    def get_widget(self, obj):
        try:
            results = Widget.objects.filter(organization=obj).first()

            return WidgetSerializer(results, many=False).data
        except Exception as e:
            print(f"Error while fetching widget: {e}")
            results = {}
        return results

    def get_welcomeNote(self, obj):
        return WelcomeNoteSerializer(obj.welcome_note).data

    def get_callYouBackNote(self, obj):
        return CallYouBackNoteSerializer(obj.call_you_back_note).data

    def get_outOfOfficeNote(self, obj):
        return OutOfOfficeNoteSerializer(obj.out_of_office_note).data

    def get_officeHours(self, obj):
        try:
            results = obj.office_hours.all()
            return OfficeHoursSerializer(results, many=True).data
        except Exception as e:
            results = {}
        return results

    def get_timezone(self, obj):
        return obj.timezone

    def get_auto_send_welcome_note(self, obj):
        return obj.auto_send_welcome_note

    def get_onboarded_by(self, obj):
        if obj.onboarded_by:
            return obj.onboarded_by.user.email
        return None

    def get_onboarded(self, obj):
        return obj.onboarded

    def get_auto_sent_after(self, obj):
        return obj.auto_sent_after

    class Meta:
        model = Organization
        fields = [
            "name",
            "token",
            "website",
            "team_name",
            "onboarded",
            "widget",
            "welcomeNote",
            "callYouBackNote",
            "outOfOfficeNote",
            "officeHours",
            "timezone",
            "auto_send_welcome_note",
            "onboarded",
            "onboarded_by",
            "auto_sent_after",
        ]


class OrganizationSerializer(serializers.ModelSerializer):

    # add a revere relationship field (widget) here
    # widget = WidgetSerializer()

    class Meta:
        model = Organization
        fields = ["name", "token", "website", "team_name", "onboarded"]


class ClientSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    organization = OrganizationSerializerCustom()

    class Meta:
        model = Client
        fields = [
            "user",
            "job_title",
            "department",
            "role",
            "organization",
            "onboarded",
        ]


class EndUserListSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    last_login = serializers.SerializerMethodField()

    def get_id(self, obj):
        return obj.user.id

    def get_first_name(self, obj):
        return obj.user.first_name

    def get_last_name(self, obj):
        return obj.user.last_name

    def get_email(self, obj):
        return obj.user.email

    def get_is_online(self, obj):
        return obj.user.is_online

    def get_last_login(self, obj):
        return obj.user.last_login

    class Meta:
        model = EndUser
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "is_online",
            "last_login",
            "is_trial",
            "role",
            "total_sessions",
            "trial_type",
            "priority",
            "company",
        ]


class ClientMemberSerializer(serializers.ModelSerializer):

    id = serializers.SerializerMethodField()
    photo = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    lastLoginTimestamp = serializers.SerializerMethodField()

    def get_id(self, obj):
        return obj.user.id

    def get_photo(self, obj):
        return obj.user.photo

    def get_name(self, obj):
        return obj.user.first_name + " " + obj.user.last_name

    def get_email(self, obj):
        return obj.user.email

    def get_role(self, obj):
        return obj.role

    def get_lastLoginTimestamp(self, obj):
        return obj.user.last_login

    class Meta:
        model = Client
        fields = [
            "id",
            "photo",
            "name",
            "email",
            "role",
            "lastLoginTimestamp",
        ]


class FeatureFlagConnectSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeatureFlagConnect
        fields = ["feature_name", "enabled"]
