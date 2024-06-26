from django.db import models
from django.contrib.auth.models import (
    BaseUserManager,
    AbstractBaseUser,
    PermissionsMixin,
    Group,
    Permission,
)
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from infra_utils.models import CreatedModifiedModel
from user.constants import (
    SKIPPED,
    NOT_APPLICABLE,
    COMPLETED,
    PENDING,
)


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

# Banner types
BANNER_TYPES = [("ooo", "OOO"), ("info", "INFO")]


class UserManager(BaseUserManager):
    def create_user(self, email, phone, password, **extra_fields):
        """
        Use phone, password, and the additional fields to create and save user
        """
        if not phone and not email:
            raise TypeError("User must have an phone or email")

        if not phone:
            user = self.model(email=email, **extra_fields)
        else:
            user = self.model(phone=phone, **extra_fields)

        user.set_password(password)
        user.is_active = True

        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Use email, password, and the additional fields to create and save superuser
        """
        user = self.create_user(email, None, password, **extra_fields)
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
    def create_enduser(self, phone, organization_name, **extra_fields):
        if not phone:
            raise ValueError("The phone field must be set")
        # email = self.normalize_email(email)

        organization = Organization.objects.filter(name=organization_name).first()

        if not organization:
            raise ValueError("The organization does not exist")

        user_account = User.objects.create(
            phone=phone,
            password=generate_random_string(),
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
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(
        max_length=255, unique=True, db_index=True, blank=True, null=True
    )
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_online = models.BooleanField(default=False)
    last_login = models.DateTimeField(auto_now=True)
    photo = models.TextField(blank=True, null=True, default="")
    phone = models.CharField(
        max_length=25, blank=True, null=True, default="", unique=True
    )

    USERNAME_FIELD = "email"

    objects = UserManager()

    def __str__(self):
        return self.phone

    def get_tokens(self):
        refresh = RefreshToken.for_user(self)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}

    def set_online_status(self, status: bool) -> None:
        self.is_online = status
        self.save()

    def clean(self):
        # Custom validation to ensure that either email or phone is provided
        if not self.email and not self.phone:
            raise ValidationError(
                "Either an email address or a phone number must be provided."
            )

    def save(self, *args, **kwargs):
        self.clean()  # Call the clean method to perform validation checks
        super(User, self).save(*args, **kwargs)


class Organization(CreatedModifiedModel):
    name = models.CharField(max_length=256)
    country = models.CharField(max_length=256, blank=True, default="")
    website = models.CharField(max_length=256, blank=True, default="")
    token = models.UUIDField(max_length=64, default=uuid.uuid4, editable=False)
    auto_send_welcome_note = models.BooleanField(default=True)
    auto_sent_after = models.CharField(
        max_length=5, blank=True, default="30", null=True
    )

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
    onboarded_by = models.OneToOneField(
        "Client",
        on_delete=models.SET_NULL,
        null=True,
        related_name="onboarded_organization",
    )

    # Any other specific fields for Organization

    # You might want to add a __str__ method to display something meaningful in the admin
    def __str__(self):
        return self.name


class OfficeHours(CreatedModifiedModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="office_hours"
    )
    weekday = models.IntegerField(choices=WEEKDAYS)
    open_time = models.TimeField()
    close_time = models.TimeField()
    is_open = models.BooleanField(default=True)
    # timezone offset in mins
    timezone_offset = models.IntegerField(default=0, blank=True, null=True)

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
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="client")
    job_title = models.CharField(max_length=256, null=True, blank=True)
    department = models.CharField(max_length=256, null=True, blank=True)
    # team_office_hours = models.CharField(max_length=256)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        related_name="clients",
        null=True,
    )
    role = models.CharField(max_length=200, choices=ROLE_CHOICES, default=STANDARD_USER)
    onboarded = models.BooleanField(default=False)
    is_client_online = models.BooleanField(default=True)

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

    CHECK_IN_STATUS_CHOICES = [
        (SKIPPED, "Skipped"),
        (NOT_APPLICABLE, "Not Applicable"),
        (COMPLETED, "Completed"),
        (PENDING, "Pending"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="end_user")
    organization = models.ForeignKey(
        Organization, on_delete=models.DO_NOTHING, related_name="end_users"
    )
    is_trial = models.BooleanField(default=True)
    role = models.CharField(max_length=200, null=True, blank=True)
    total_sessions = models.IntegerField(default=0)
    trial_type = models.CharField(max_length=200, null=True, blank=True)
    priority = models.CharField(max_length=200, choices=PRIORITY_CHOICES, default=LOW)
    company = models.CharField(max_length=200, null=True, blank=True)
    linkedin = models.TextField(null=True, blank=True)
    city = models.CharField(max_length=200, null=True, blank=True)
    country = models.CharField(max_length=200, null=True, blank=True)
    welcome_note_sent = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False, blank=True, null=True)

    # CheckIn Feature related fields
    check_in_status = models.CharField(
        max_length=200, choices=CHECK_IN_STATUS_CHOICES, default=PENDING
    )

    objects = EndUserManager()

    def __str__(self):
        return self.user.phone + " - " + self.organization.name

    def get_user_details(self):
        return {
            "username": f"{self.user.first_name} {self.user.last_name}",
            "company": self.company,
            "linkedin": self.linkedin,
            "city": self.city,
            "country": self.country,
            "is_new": self.is_new,
            "phone": self.user.phone,
        }


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

    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name="widgets"
    )
    avatar = models.CharField(max_length=50, choices=AVATAR_CHOICES)
    position = models.CharField(max_length=50, choices=POSITION_CHOICES)
    is_active = models.BooleanField(default=True)
    color_1 = models.CharField(max_length=50, default="#3A4CF0")
    color_2 = models.CharField(max_length=50, default="#E01D5A")


class FeatureFlagConnect(models.Model):
    feature_name = models.CharField(max_length=100, unique=True)
    enabled = models.BooleanField(default=False)
    organization = models.ManyToManyField(
        Organization,
        blank=True,
        help_text="Organizations for whom the feature is enabled",
        related_name="feature_flags_connect",
    )

    def __str__(self):
        return self.feature_name


class ClientBanner(CreatedModifiedModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="client_banners"
    )
    banner = models.TextField()
    hyperlink = models.CharField(max_length=256)
    is_active = models.BooleanField(default=True)
    banner_type = models.CharField(max_length=50, choices=BANNER_TYPES, default="ooo")

    def __str__(self):
        return self.organization.name


class CheckInFeature(CreatedModifiedModel):
    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name="check_in_feature"
    )
    master_switch = models.BooleanField(default=True)
    skip_switch = models.BooleanField(default=False)
    support_email = models.EmailField(max_length=255, blank=True, default="")

    def __str__(self):
        return self.organization.name + " - " + self.support_email


class UserSession(CreatedModifiedModel):
    session_id = models.CharField(primary_key=True, max_length=256, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_sessions"
    )
    storage_url = models.TextField(null=True, blank=True)
    initial_events = models.JSONField(default=list, blank=True, null=True)

    def __str__(self):
        return self.session_id
