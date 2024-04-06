from django.core.mail import send_mail
from django.conf import settings
from django_q.tasks import async_task
from django.utils import timezone
from datetime import timedelta

import pytz
import requests
import logging


logger = logging.getLogger("django")
DEFAULT_FROM_EMAIL = settings.DEFAULT_FROM_EMAIL


def send_email_task(subject, body, html_body, from_email, to_email):
    send_mail(
        subject,
        body,
        f"PingBase <{from_email}>",
        [to_email],
        fail_silently=False,
        html_message=html_body,
    )


def send_code_email_task(subject, html_email_body, from_email, to_email):
    send_mail(
        subject,
        None,
        f"PingBase <{from_email}>",
        [to_email],
        fail_silently=False,
        html_message=html_email_body,
    )


class Mail:
    @staticmethod
    def send_email(data):
        # Schedule the standalone email function as an asynchronous task

        html_body = data.get("html_email_body", None)
        task_id = async_task(
            "user.utils.send_email_task",
            data["email_subject"],
            data["email_body"],
            html_body,
            DEFAULT_FROM_EMAIL,
            data["to_email"],
        )
        print(f"Email send task scheduled with ID: {task_id}")

    @staticmethod
    def send_code_email(data):
        task_id = async_task(
            "user.utils.send_code_email_task",
            data["email_subject"],
            data["html_email_body"],
            DEFAULT_FROM_EMAIL,
            data["to_email"],
        )
        print(f"Email send task scheduled with ID: {task_id}")


def get_linkedIn_url(email: str):
    if not email:
        return None
    RC_BASE_URL = settings.REVERSE_CONTACT_BASE_URL
    RC_API_KEY = settings.REVERSE_CONTACT_API_KEY
    url = f"{RC_BASE_URL}/enrichment"
    try:
        logger.info("making the request")
        querystring = {"apikey": f"{RC_API_KEY}", "email": f"{email}"}

        res = requests.get(
            url,
            headers={
                "Content-Type": "application/json",
            },
            params=querystring,
        )
        data = res.json()
        if "success" in data:
            try:
                linkedin_url = data["person"]["linkedInUrl"]
                return linkedin_url
            except AttributeError:
                logger.error(f"No LinkedIn URL found for {email}")
                return None
    except requests.exceptions.RequestException as e:
        print(f"Error while fetching LinkedIn URL: {e}")
        return None


def is_request_within_office_hours(organization):
    # Get the current time in UTC
    now_utc = timezone.now()

    # Find the office hours entry for the organization today
    today = (now_utc.weekday() + 1) % 7 or 7
    try:
        office_hours = organization.office_hours.get(weekday=today)
    except OfficeHours.DoesNotExist:
        # Assuming if there's no entry, the office is closed
        return False

    if not office_hours.is_open:
        return False

    # Adjust the current time for the organization's timezone
    timezone_offset = timedelta(minutes=office_hours.timezone_offset)
    now_local = now_utc + timezone_offset

    # Check if the current time is within office hours
    open_time = (
        timezone.datetime.combine(
            now_utc.date(), office_hours.open_time, tzinfo=pytz.UTC
        )
        + timezone_offset
    )
    close_time = (
        timezone.datetime.combine(
            now_utc.date(), office_hours.close_time, tzinfo=pytz.UTC
        )
        + timezone_offset
    )

    return open_time <= now_local < close_time
