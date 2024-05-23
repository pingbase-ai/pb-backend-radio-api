from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.db.models import F
from dyte.models import DyteMeeting, DyteAuthToken
from django.conf import settings
from user.models import EndUser, Widget, User, OfficeHours, ClientBanner
from django_q.tasks import schedule
from datetime import timedelta
from django.utils import timezone
from .utils import LinkedIn, schedule_next_update_for_organization
from pusher_channel_app.utils import publish_event_to_client
from .constants import BANNER_OOO_TEXT, BANNER_OOO_HYPERLINK_TEXT


import logging

logger = logging.getLogger("django")


@receiver(post_save, sender=EndUser)
def create_dyte_meeting(sender, instance, created, **kwargs):
    """
    Signal to create a DyteMeeting instance and auth token for the endUser.
    """
    logger.info(f"create_dyte_meeting signal triggered for endUser: {instance}")
    if created:
        try:
            # Create a DyteMeeting instance for the endUser
            meeting = DyteMeeting.create_meeting(instance)

            # Create auth token for the endUser
            authToken = DyteAuthToken.create_dyte_auth_token(
                meeting, False, end_user=instance
            )
        except Exception as e:
            logger.error(f"Error while creating Dyte meeting and auth token: {e}")


@receiver(post_save, sender=EndUser)
def send_welcome_note(sender, instance, created, **kwargs):
    if (created or not instance.welcome_note_sent) and (
        instance.organization.auto_send_welcome_note
    ):
        delay_time = int(instance.organization.auto_sent_after)
        schedule(
            "user.tasks.send_voice_note",
            instance.user.id,
            "welcome_note",
            schedule_type="O",
            next_run=timezone.now() + timedelta(seconds=delay_time),
        )


@receiver(post_save, sender=EndUser)
def fetch_linkedIn_url(sender, instance, created, **kwargs):
    if created:
        try:
            if not instance.linkedin:
                email = instance.user.email
                # fetch the linkedIn URL ASYNC
                LinkedIn.get_linkedIn_url_async(email)
        except Exception as e:
            logger.error(f"Error while fetching LinkedIn URL: {e}")


@receiver(post_save, sender=Widget)
def widget_updated(sender, instance, created, **kwargs):
    if not created:
        try:
            pusher_data_obj = {
                "source_event_type": "widget_status_check",
            }

            publish_event_to_client(
                instance.organization.token,
                "private",
                "master-event",
                pusher_data_obj,
            )
        except Exception as e:
            logger.error(f"Error while sending notification to all widgets: {e}")


@receiver(pre_save, sender=User)
def check_photo_change(sender, instance, **kwargs):
    if instance.pk:  # Check if the instance is not new
        # Fetch the old data from the database
        old_photo = (
            User.objects.filter(pk=instance.pk).values_list("photo", flat=True).first()
        )
        if old_photo != instance.photo:
            # now update the client photo in all the meetings.
            logger.info(
                f"Detected photo change for user: {instance} and new photo is {instance.photo}"
            )
            client = instance.client

            if client and instance.photo:
                # TODO update the below logic to be more precise
                meetings = DyteMeeting.objects.all()
                for meeting in meetings:
                    try:
                        client_auth_token_obj = DyteAuthToken.objects.filter(
                            is_parent=True, client=client, meeting=meeting
                        ).first()
                        if client_auth_token_obj:
                            # delete the old token from dyte servers
                            try:
                                DyteAuthToken.delete_dyte_auth_token(
                                    client_auth_token_obj.auth_id, meeting.meeting_id
                                )
                            except Exception as e:
                                logger.error(
                                    f"Error while deleting Dyte auth token from dyte servers"
                                )
                            updated_auth_token_obj = (
                                DyteAuthToken.update_dyte_auth_token(
                                    client_auth_token_obj, instance.photo
                                )
                            )
                        else:
                            logger.info(
                                f"No Dyte auth token found for client: {client} and meeting: {meeting}"
                            )
                    except Exception as e:
                        logger.error(
                            f"Error while updating Dyte auth token for client: {e} for meeting: {meeting}"
                        )

            elif not instance.photo:
                logger.info(f"Photo removed for user: {instance}")
                meetings = DyteMeeting.objects.all()
                for meeting in meetings:
                    client_auth_token_obj = DyteAuthToken.objects.filter(
                        is_parent=True, client=client, meeting=meeting
                    ).first()
                    if client_auth_token_obj:
                        try:
                            DyteAuthToken.delete_dyte_auth_token(
                                client_auth_token_obj.auth_id, meeting.meeting_id
                            )
                        except Exception as e:
                            logger.error(
                                f"Error while deleting Dyte auth token from dyte servers: {e}"
                            )
                try:
                    dyteAuthObjs = DyteAuthToken.objects.filter(
                        is_parent=True, client=client
                    ).delete()
                    logger.info(f"Deleted Dyte auth tokens: {dyteAuthObjs}")
                except Exception as e:
                    logger.error(
                        f"Error while updating Dyte auth token for client: {e} for meeting: {meeting}"
                    )


@receiver(post_save, sender=OfficeHours)
@receiver(post_delete, sender=OfficeHours)
def handle_office_hours_update(sender, instance, created, **kwargs):
    try:
        pass
        # if this is a new instance, create a new ClientBanner
        if created:
            try:
                ClientBanner.objects.create(
                    organization=instance.organization,
                    banner=BANNER_OOO_TEXT,
                    hyperlink=BANNER_OOO_HYPERLINK_TEXT,
                    banner_type="ooo",
                    is_active=False,
                )
            except Exception as e:
                logger.error(f"Error while creating new ClientBanner: {e}")

        schedule_next_update_for_organization(instance.organization)
    except Exception as e:
        logger.error(f"Error while scheduling office hours: {e}")
