from django.core.management.base import BaseCommand
from user.tasks import update_banner_status


class Command(BaseCommand):
    help = "Initial setup for updating banner status for all organizations"

    def handle(self, *args, **kwargs):
        update_banner_status()
        self.stdout.write(
            self.style.SUCCESS(
                "Successfully scheduled banner updates for all organizations"
            )
        )
