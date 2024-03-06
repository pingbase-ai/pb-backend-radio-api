from django.core.mail import send_mail
from django.conf import settings
from django_q.tasks import async_task

DEFAULT_FROM_EMAIL = settings.DEFAULT_FROM_EMAIL


def send_email_task(subject, body, from_email, to_email):
    send_mail(subject, body, from_email, [to_email], fail_silently=False)


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
