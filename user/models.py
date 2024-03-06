from django.db import models
from django.contrib.auth.models import (
    BaseUserManager,
    AbstractBaseUser,
    PermissionsMixin,
    Group,
    Permission,
)
from rest_framework_simplejwt.tokens import RefreshToken
from infra_utils.models import CreatedModifiedModel
from django.contrib.auth.models import AbstractUser

from infra_utils.utils import generate_random_string

import uuid
import datetime

# Create your models here.
WEEKDAYS = [
    (1, ("Monday")),
    (2, ("Tuesday")),
    (3, ("Wednesday")),
    (4, ("Thursday")),
    (5, ("Friday")),
    (6, ("Saturday")),
    (7, ("Sunday")),
]


class UserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        """
        Use email, password, and the additional fields to create and save user
        """
        if not email:
            raise TypeError("User must have an email")

        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)

        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Use email, password, and the additional fields to create and save superuser
        """
        user = self.create_user(email, password, **extra_fields)
        user.is_superuser = True
        user.is_active = True
        user.is_verified = True
        user.is_staff = True

        user.save()
        return user


class CustomPermissionsMixin(PermissionsMixin):
    groups = models.ManyToManyField(
        Group,
        verbose_name="groups",
        blank=True,
        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
        related_name="user_set_custom",  # Custom related_name
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name="user permissions",
        blank=True,
        help_text="Specific permissions for this user.",
        related_name="user_set_custom",  # Custom related_name
        related_query_name="user",
    )


class EndUserManager(BaseUserManager):
    def create_enduser(
        self, first_name, last_name, email, organization_name, **extra_fields
    ):
        print("hello there")
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)

        organization = Organization.objects.filter(name=organization_name).first()

        if not organization:
            raise ValueError("The organization does not exist")

        user_account = User.objects.create(
            email=email,
            password=generate_random_string(),
            first_name=first_name,
            last_name=last_name,
        )
        # enduser = self.model(
        #     username=username, email=email, client=client, **extra_fields
        # )
        user_account.set_unusable_password()
        user_account.is_superuser = False
        user_account.is_active = False
        user_account.is_verified = False
        user_account.is_staff = False
        user_account.save(using=self._db)

        enduser = self.model(
            user=user_account, organization=organization, **extra_fields
        )
        enduser.save(using=self._db)
        return enduser


class User(AbstractBaseUser, CustomPermissionsMixin):
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(max_length=255, unique=True, db_index=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"

    objects = UserManager()

    def __str__(self):
        return self.first_name + " " + self.last_name + " " + self.email

    def get_tokens(self):
        refresh = RefreshToken.for_user(self)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}


class Organization(CreatedModifiedModel):
    name = models.CharField(max_length=256)
    country = models.CharField(max_length=256, blank=True, default="")
    website = models.CharField(max_length=256, blank=True, default="")
    token = models.UUIDField(max_length=64, default=uuid.uuid4, editable=False)
    auto_send_welcome_note = models.BooleanField(default=True)

    welcome_note = models.ForeignKey(
        "WelcomeNote", on_delete=models.DO_NOTHING, null=True, blank=True
    )
    call_you_back_note = models.ForeignKey(
        "CallYouBackNote", on_delete=models.DO_NOTHING, null=True, blank=True
    )

    out_of_office_note = models.ForeignKey(
        "OutOfOfficeNote", on_delete=models.DO_NOTHING, null=True, blank=True
    )
    timezone = models.CharField(max_length=256, blank=True, default="")
    team_name = models.CharField(max_length=256, null=True, blank=True)
    onboarded = models.BooleanField(default=False)

    # Any other specific fields for Organization

    # You might want to add a __str__ method to display something meaningful in the admin
    def __str__(self):
        return self.name


class OfficeHours(CreatedModifiedModel):
    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name="office_hours"
    )
    weekday = models.IntegerField(choices=WEEKDAYS)
    open_time = models.TimeField()
    close_time = models.TimeField()
    is_open = models.BooleanField(default=True)

    def get_weekday_display(self):
        return dict(WEEKDAYS)[self.weekday]

    def __str__(self):
        return self.organization.name + " - " + self.get_weekday_display()

    class Meta:
        unique_together = ("organization", "weekday")


class Client(CreatedModifiedModel):
    ADMIN = "admin"
    STANDARD_USER = "standard_user"
    # Add more role options here

    ROLE_CHOICES = [
        (ADMIN, "Admin"),
        (STANDARD_USER, "Standard User"),
        # Add more role choices here
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    job_title = models.CharField(max_length=256, null=True, blank=True)
    department = models.CharField(max_length=256, null=True, blank=True)
    # team_office_hours = models.CharField(max_length=256)
    organization = models.ForeignKey(
        Organization, on_delete=models.DO_NOTHING, related_name="clients"
    )
    role = models.CharField(max_length=200, choices=ROLE_CHOICES, default=STANDARD_USER)
    onboarded = models.BooleanField(default=False)

    def __str__(self):
        return self.organization.name + " - " + self.user.email


class EndUser(CreatedModifiedModel):

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    PRIORITY_CHOICES = [
        (LOW, "Low"),
        (MEDIUM, "Medium"),
        (HIGH, "High"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(
        Organization, on_delete=models.DO_NOTHING, related_name="end_users"
    )
    is_trial = models.BooleanField(default=True)
    role = models.CharField(max_length=200, null=True, blank=True)
    total_sessions = models.IntegerField(default=0)
    trail_type = models.CharField(max_length=200, null=True, blank=True)
    priority = models.CharField(max_length=200, choices=PRIORITY_CHOICES, default=LOW)

    objects = EndUserManager()

    def __str__(self):
        return (
            self.user.first_name
            + " "
            + self.user.last_name
            + " - "
            + self.organization.name
        )


class WelcomeNote(CreatedModifiedModel):
    title = models.CharField(max_length=256)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    storage_url = models.TextField()
    play_time = models.DurationField(default=datetime.timedelta(seconds=0))

    def __str__(self):
        return self.title


class CallYouBackNote(CreatedModifiedModel):
    title = models.CharField(max_length=256)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    storage_url = models.TextField()
    play_time = models.DurationField(default=datetime.timedelta(seconds=0))

    def __str__(self):
        return self.title


class OutOfOfficeNote(CreatedModifiedModel):
    title = models.CharField(max_length=256)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    storage_url = models.TextField()
    play_time = models.DurationField(default=datetime.timedelta(seconds=0))

    def __str__(self):
        return self.title


class Subscription(CreatedModifiedModel):

    PRO = "PRO"
    STANDARD = "STANDARD"
    ENTERPRISE = "ENTERPRISE"

    PRO_PRICE = 499
    STANDARD_PRICE = 199
    ENTERPRISE_PRICE = 999

    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"

    PLAN_RENEVAL_CHOICES = (
        (MONTHLY, "Monthly"),
        (QUARTERLY, "Quarterly"),
    )

    PLAN_CHOICES = (
        (PRO, "Pro"),
        (STANDARD, "Standard"),
        (ENTERPRISE, "Enterprise"),
    )

    PRICE_CHOICES = (
        (PRO_PRICE, "Pro Price"),
        (STANDARD_PRICE, "Standard Price"),
        (ENTERPRISE_PRICE, "Enterprise Price"),
    )

    organization = models.ForeignKey(
        Organization, on_delete=models.DO_NOTHING, related_name="subscriptions"
    )
    subscribed_by = models.ForeignKey(
        Client, on_delete=models.DO_NOTHING, related_name="subscriptions"
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    plan = models.CharField(max_length=256, choices=PLAN_CHOICES, default=STANDARD)
    price = models.IntegerField(choices=PRICE_CHOICES, default=STANDARD_PRICE)
    plan_time = models.CharField(
        max_length=256, choices=PLAN_RENEVAL_CHOICES, default=MONTHLY
    )

    @classmethod
    def get_active_subscription(cls, organization):
        return cls.objects.filter(organization=organization, is_active=True).first()

    def __str__(self):
        return self.organization.name + " - " + self.subscribed_by.user.email


class OnboardingSession(CreatedModifiedModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.DO_NOTHING, related_name="onboarding_session"
    )
    client = models.ForeignKey(
        Client, on_delete=models.DO_NOTHING, related_name="onboarding_session"
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return self.organization.name + " - " + self.client.user.email


class Widget(models.Model):

    AVATAR_CHOICES = [
        ("avatar1", "Avatar 1"),
        ("avatar2", "Avatar 2"),
        # Add more predefined avatars here
    ]

    POSITION_CHOICES = [
        ("bottom_left", "Bottom Left"),
        ("bottom_right", "Bottom Right"),
    ]

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="widgets"
    )
    avatar = models.CharField(max_length=50, choices=AVATAR_CHOICES)
    position = models.CharField(max_length=50, choices=POSITION_CHOICES)
