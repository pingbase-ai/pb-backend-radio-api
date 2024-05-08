from django.core.mail import send_mail
from django.conf import settings
from django_q.tasks import async_task
from django.utils import timezone
from datetime import timedelta
from user.models import User
from pusher_channel_app.utils import publish_event_to_client

import pytz
import requests
import logging


logger = logging.getLogger("django")
DEFAULT_FROM_EMAIL = settings.DEFAULT_FROM_EMAIL


def remove_spaces_from_text(text: str) -> str:
    return text.replace(" ", "_")


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


def get_linkedIn_url(email: str) -> None:
    if not email:
        return None
    RC_BASE_URL = settings.REVERSE_CONTACT_BASE_URL
    RC_API_KEY = settings.REVERSE_CONTACT_API_KEY
    url = f"{RC_BASE_URL}/enrichment"
    try:
        user = User.objects.get(email=email)
        endUser = user.end_user
    except Exception as e:
        logger.error(f"Error while fetching user : {e}")
        return

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
                endUser.linkedin = linkedin_url
                endUser.save()
                # send the pusher event to all the clients
                pusher_data_obj = {
                    "source_event_type": "end_user_details_updated",
                    "id": str(endUser.id),
                    "sender": f"{str(user.first_name)} {str(user.last_name)}",
                    "company": f"{endUser.company}",
                    "timestamp": str(timezone.now()),
                    "role": f"{endUser.role}",
                }
                try:
                    publish_event_to_client(
                        endUser.organization.token,
                        "private",
                        "enduser-event",
                        pusher_data_obj,
                    )

                except Exception as e:
                    logger.error(
                        f"Error while sending pusher event on enduser details updation{e}"
                    )
            except AttributeError:
                logger.warning(f"No LinkedIn URL found for {email}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error while fetching LinkedIn URL: {e}")


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


class LinkedIn:
    @staticmethod
    def get_linkedIn_url_async(email: str) -> None:
        task_id = async_task("user.utils.get_linkedIn_url", email)
        logger.info(f"LinkedIn URL fetch task is scheduled with task ID: {task_id}")


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
