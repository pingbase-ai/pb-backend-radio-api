from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib import auth
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from infra_utils.utils import password_rule_check
from .models import (
    EndUser,
    OfficeHours,
    Widget,
    WelcomeNote,
    CallYouBackNote,
    OutOfOfficeNote,
    Client,
    Organization,
)

# from .models import Customer


User = get_user_model()


class EndUserSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    organization_name = serializers.CharField(
        write_only=True,
    )

    class Meta:
        model = EndUser
        fields = [
            "first_name",
            "last_name",
            "email",
            "organization_name",
            "is_trial",
            "role",
            "total_sessions",
            "trail_type",
            "priority",
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
        if not user.is_verified:
            raise AuthenticationFailed("Your Email is not verified")

        tokens = user.get_tokens()

        access_token = tokens["access"]
        refresh_token = tokens["refresh"]

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
        fields = ["avatar", "position"]


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


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["name", "token", "website", "team_name", "onboarded"]


class ClientSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    organization = OrganizationSerializer()

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
            "trail_type",
            "priority",
            "company",
        ]
