from django.core.mail import send_mail
from django.conf import settings
from django_q.tasks import async_task, schedule
from django_q.models import Schedule, OrmQ
from django.utils import timezone
from datetime import timedelta, datetime, UTC
from user.models import User, Organization
from pusher_channel_app.utils import publish_event_to_client
from functools import lru_cache


import pytz
import requests
import logging


logger = logging.getLogger("django")
DEFAULT_FROM_EMAIL = settings.DEFAULT_FROM_EMAIL


@lru_cache(maxsize=1000)
def get_local_time_from_utc(utc_time, timezone_str):
    local_tz = pytz.timezone(timezone_str)
    return utc_time.astimezone(local_tz)


def is_office_open(office_hours, timezone_str):
    current_utc_time = datetime.now(UTC).replace(tzinfo=pytz.utc)
    current_local_time = get_local_time_from_utc(current_utc_time, timezone_str)

    weekday = current_local_time.weekday() + 1  # Monday is 1 and Sunday is 7

    if office_hours:
        for office_hour in office_hours:
            if office_hour.weekday == weekday:
                if office_hour.is_open:
                    open_time = current_local_time.replace(
                        hour=office_hour.open_time.hour,
                        minute=office_hour.open_time.minute,
                        second=0,
                        microsecond=0,
                    )
                    close_time = current_local_time.replace(
                        hour=office_hour.close_time.hour,
                        minute=office_hour.close_time.minute,
                        second=0,
                        microsecond=0,
                    )
                    return (
                        open_time <= current_local_time <= close_time,
                        open_time,
                        close_time,
                    )
    return False, None, None


def schedule_next_update(time_to_run, organization_id, action):
    task_name = f"Update Banner Status {organization_id} {action}"
    schedule(
        "user.tasks.update_banner_status_for_organisation",
        organization_id,
        action,
        name=task_name,
        schedule_type="O",
        next_run=time_to_run,
    )


def cancel_scheduled_tasks(organization_id):
    Schedule.objects.filter(
        name__startswith=f"Update Banner Status {organization_id}"
    ).delete()


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
                if not data:
                    return
                if not data["person"]:
                    return

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
            except Exception as e:
                logger.error(f"Error while fetching LinkedIn URL: {e}")
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


def schedule_next_update_for_organization(organization):
    office_hours = organization.office_hours.all()
    if not office_hours or not organization.timezone:
        return

    is_open, open_time, close_time = is_office_open(office_hours, organization.timezone)
    next_run = close_time if is_open else open_time

    if next_run:
        cancel_scheduled_tasks(organization.id)
        action = "close" if is_open else "open"
        schedule_next_update(next_run, organization.id, action)


def update_banner_status_for_organisation(organization_id, action="close"):

    task_name = f"Update Banner Status {organization_id} {action}"
    if OrmQ.objects.filter(name=task_name, lock__isnull=False).exists():
        logger.info(
            f"Task for organization {organization_id} is already running. Skipping this run."
        )
        return

    try:
        organization = Organization.objects.prefetch_related("office_hours").get(
            id=organization_id
        )
    except Organization.DoesNotExist:
        logger.error(f"Organization {organization_id} does not exist.")
        return

    office_hours = organization.office_hours.all()
    if not office_hours or not organization.timezone:
        return

    is_open, open_time, close_time = is_office_open(office_hours, organization.timezone)

    banner = (
        organization.client_banners.filter(banner_type="ooo")
        .select_related("organization")
        .first()
    )

    if banner:
        if action == "close" and not is_open:
            banner.is_active = True
            next_run = open_time
            next_action = "open"
        elif action == "open" and is_open:
            banner.is_active = False
            next_run = close_time
            next_action = "close"
        else:
            logger.info(
                f"No action needed for organization {organization_id} with action {action}."
            )
            return

        banner.save()
        logger.info(
            f'Updated banner status for organization {organization.name} to {"active" if banner.is_active else "inactive"}'
        )

        if next_run:
            schedule_next_update(next_run, organization.id, next_action)
