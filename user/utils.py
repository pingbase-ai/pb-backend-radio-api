from django.core.mail import send_mail
from django.conf import settings
from django_q.tasks import async_task
import requests
import logging

logger = logging.getLogger("django")
DEFAULT_FROM_EMAIL = settings.DEFAULT_FROM_EMAIL


def send_email_task(subject, body, from_email, to_email):
    send_mail(subject, body, from_email, [to_email], fail_silently=False)


def send_code_email_task(subject, code_snippet, from_email, to_email):
    email_body = f"Here is your code snippet:\n\n{code_snippet}"
    send_mail(subject, email_body, from_email, [to_email], fail_silently=False)


class Mail:
    @staticmethod
    def send_email(data):
        # Schedule the standalone email function as an asynchronous task
        task_id = async_task(
            "user.utils.send_email_task",
            data["email_subject"],
            data["email_body"],
            DEFAULT_FROM_EMAIL,
            data["to_email"],
        )
        print(f"Email send task scheduled with ID: {task_id}")

    @staticmethod
    def send_code_email(data):
        task_id = async_task(
            "user.utils.send_code_email_task",
            data["email_subject"],
            data["code_snippet"],
            DEFAULT_FROM_EMAIL,
            data["to_email"],
        )
        print(f"Email send task scheduled with ID: {task_id}")


def get_linkedIn_url(email: str):
    if not email:
        return None
    UPLEAD_BASE_URL = settings.UPLEAD_BASE_URL
    UPLEAD_API_KEY = settings.UPLEAD_API_KEY
    url = f"{UPLEAD_BASE_URL}/person-search"
    data = {"email": email}
    try:
        logger.info("making the request")
        res = requests.post(
            url,
            params={"email": email},
            headers={
                "Authorization": f"{UPLEAD_API_KEY}",
                "Content-Type": "application/json",
            },
            json=data,
        )
        logging.info(f"res--{res.status_code}--{res.json()}--{res.reason}--{res.text}")
        # res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        print(f"Error while fetching LinkedIn URL: {e}")
        return None
