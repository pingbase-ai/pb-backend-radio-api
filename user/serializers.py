from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib import auth
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
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
    tokens = serializers.CharField(max_length=68, min_length=8, read_only=True)

    class Meta:
        model = User
        fields = ["email", "password", "tokens"]

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

        return {"email": user.email, "tokens": user.get_tokens}


class RequestPasswordResetEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


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
        fields = ["id", "first_name", "last_name", "email", "is_active"]


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
        fields = ["name", "token", "website", "team_name"]


class ClientSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    organization = OrganizationSerializer()

    class Meta:
        model = Client
        fields = ["user", "job_title", "department", "role", "organization"]
