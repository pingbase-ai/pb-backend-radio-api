from django.apps import AppConfig
from django_q.models import Schedule
from django_q.tasks import schedule


import datetime


class UserConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "user"

    def ready(self) -> None:
        super().ready()

        import user.signals

        try:
            # Schedule the weekly banner update task if it does not already exist
            if not Schedule.objects.filter(name="Weekly Banner Update").exists():
                # Calculate the next Sunday
                next_sunday = datetime.datetime.now() + datetime.timedelta(
                    days=(6 - datetime.datetime.now().weekday())
                )
                next_sunday = next_sunday.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                schedule(
                    "user.tasks.update_banner_status",
                    name="Weekly Banner Update",
                    schedule_type="W",
                    repeats=-1,  # Repeat indefinitely
                    next_run=next_sunday,
                )
        except Exception as e:
            print(f"Error while scheduling weekly banner update task: {e}")
            pass
