from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.db.models import F
from dyte.models import DyteMeeting, DyteAuthToken
from django.conf import settings
from user.models import (
    EndUser,
    Widget,
    User,
    OfficeHours,
    ClientBanner,
    Client,
    CheckInFeature,
)
from django_q.tasks import schedule
from datetime import timedelta
from django.utils import timezone
from .utils import (
    LinkedIn,
    schedule_next_update_for_organization,
    bulk_update_active_status_for_clients,
)
from pusher_channel_app.utils import (
    publish_event_to_client,
    publish_event_to_channel,
    publish_event_to_user,
)
from .constants import BANNER_OOO_TEXT, BANNER_OOO_HYPERLINK_TEXT
from django.core.cache import cache
from django_q.models import Schedule
from events.models import Event
from user.constants import (
    COMPLETED,
    SKIPPED,
    CHECKIN_SKIPPED,
    CHECKIN_COMPLETED,
    NOT_APPLICABLE,
    CHECKIN_NOT_APPLICABLE,
)
from infra_utils.utils import encode_base64
from user.tasks import send_slack_blocks_async
from user.constants import (
    get_first_enduser_invite_slack_block_template_part_1,
    get_first_enduser_invite_slack_block_template_part_2,
    get_first_enduser_invite_slack_block_template_part_3,
)
from django.db import transaction
from home.event_types import SUCCESS, MANUAL

import logging

logger = logging.getLogger("django")


@receiver(pre_save, sender=EndUser)
def watch_check_in_status(sender, instance, **kwargs):
    if instance.pk:
        old_instance = (
            sender.objects.filter(pk=instance.pk).only("check_in_status").first()
        )
        if old_instance and old_instance.check_in_status != instance.check_in_status:
            try:
                check_in_status = instance.check_in_status
                if (
                    check_in_status == COMPLETED
                    or check_in_status == SKIPPED
                    or check_in_status == NOT_APPLICABLE
                ):
                    # send a pusher notification to the user

                    pusher_data_obj = {
                        "source_event_type": "check_in_status_change",
                        "check_in_status": check_in_status,
                        "user_id": instance.user.id,
                    }

                    try:
                        publish_event_to_user(
                            instance.organization.token,
                            "private",
                            encode_base64(f"{instance.user.id}"),
                            "checkin-event",
                            pusher_data_obj,
                        )

                        publish_event_to_channel(
                            instance.organization.token,
                            "private",
                            "checkin-event",
                            pusher_data_obj,
                        )
                    except Exception as e:
                        logger.error(
                            f"Error while sending notification to enduser or client: {e}"
                        )

            except Exception as e:
                logger.error(f"Error while creating an event for check-in status: {e}")

        return


@receiver(post_save, sender=EndUser)
def send_slack_notification_on_first_enduser_login(sender, instance, created, **kwargs):
    """
    Signal to send slack notification on first enduser login.
    """
    logger.info(f"Enduser Instance: {instance} \t created: {created}")
    if created:
        logger.info(f"New enduser created: {instance}")
        with transaction.atomic():
            organization = instance.organization  # Get the organization of the new user
            total_endusers = (
                EndUser.objects.select_for_update()
                .filter(organization=organization)  # Filter by organization
                .count()
            )
            logger.info(f"Total endusers for organization: {total_endusers}")
        if total_endusers == 1:
            try:
                # send a slack notification
                company = instance.organization.name
                email = instance.user.email
                phone = instance.user.phone
                blocks = [
                    *get_first_enduser_invite_slack_block_template_part_1(company),
                    *get_first_enduser_invite_slack_block_template_part_2(email, phone),
                    *get_first_enduser_invite_slack_block_template_part_3(),
                ]
                slack_hook = settings.SLACK_APP_SIGNUPS_WEBHOOK_URL

                data = {
                    "blocks": blocks,
                    "slack_hook": slack_hook,
                }
                try:
                    send_slack_blocks_async(data)
                except Exception as e:
                    logger.error(
                        f"Error while sending slack notification from view: {e}"
                    )
            except Exception as e:
                logger.error(f"Error while sending slack notification: {e}")


# @receiver(post_save, sender=EndUser)
# def create_dyte_meeting(sender, instance, created, **kwargs):
#     """
#     Signal to create a DyteMeeting instance and auth token for the endUser.
#     """
#     logger.info(f"create_dyte_meeting signal triggered for endUser: {instance}")
#     if created:
#         try:
#             # Create a DyteMeeting instance for the endUser
#             meeting = DyteMeeting.create_meeting(instance)

#             # Create auth token for the endUser
#             authToken = DyteAuthToken.create_dyte_auth_token(
#                 meeting, False, end_user=instance
#             )
#         except Exception as e:
#             logger.error(f"Error while creating Dyte meeting and auth token: {e}")


# @receiver(post_save, sender=EndUser)
# def send_welcome_note(sender, instance, created, **kwargs):
#     if (created or not instance.welcome_note_sent) and (
#         instance.organization.auto_send_welcome_note
#     ):
#         delay_time = int(instance.organization.auto_sent_after)
#         schedule(
#             "user.tasks.send_voice_note",
#             instance.user.id,
#             "welcome_note",
#             schedule_type="O",
#             next_run=timezone.now() + timedelta(seconds=delay_time),
#         )


# @receiver(post_save, sender=EndUser)
# def fetch_linkedIn_url(sender, instance, created, **kwargs):
#     if created:
#         try:
#             if not instance.linkedin:
#                 email = instance.user.email
#                 # fetch the linkedIn URL ASYNC
#                 LinkedIn.get_linkedIn_url_async(email)
#         except Exception as e:
#             logger.error(f"Error while fetching LinkedIn URL: {e}")


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
        # if this is a new instance, create a new ClientBanner
        if created:
            try:
                # check if the organization already has an OOO banner

                existing_banner = ClientBanner.objects.filter(
                    organization=instance.organization, banner_type="ooo"
                ).first()
                if not existing_banner:
                    ClientBanner.objects.create(
                        organization=instance.organization,
                        banner=BANNER_OOO_TEXT,
                        hyperlink=BANNER_OOO_HYPERLINK_TEXT,
                        banner_type="ooo",
                        is_active=False,
                    )
            except Exception as e:
                logger.error(f"Error while creating new ClientBanner: {e}")

        bulk_update_active_status_for_clients(instance.organization.id, True)
        cache_key = f"schedule_update_{instance.organization.id}"
        if not cache.get(cache_key):
            schedule_next_update_for_organization(instance.organization)
            cache.set(cache_key, True, 30)  # Prevent re-triggering within 30 seconds

    except Exception as e:
        logger.error(f"Error while scheduling office hours: {e}")


@receiver(pre_save, sender=ClientBanner)
def alert_banner_active_status(sender, instance, **kwargs):
    if instance.pk:
        old_instance = sender.objects.filter(pk=instance.pk).only("is_active").first()
        if old_instance and old_instance.is_active != instance.is_active:

            try:

                # cancel any scheduled user status update
                task_name = f"client_status_{instance.organization.token}"
                try:
                    Schedule.objects.filter(name__startswith=f"{task_name}").delete()
                except Exception as e:
                    logger.error(f"Error while deleting existing tasks in signal: {e}")

                # toggle status for all the clients
                try:
                    if instance.is_active:
                        instance.organization.clients.update(is_client_online=False)
                    else:
                        instance.organization.clients.update(is_client_online=True)
                except Exception as e:
                    logger.error(f"Error while updating client status in signal: {e}")

                # send a pusher notification to all the clients
                try:
                    for client in instance.organization.clients.all():
                        pusher_data_obj_client = {
                            "source_event_type": "client_status_change",
                            "is_active": not instance.is_active,
                            "user_id": client.user.id,
                        }

                        publish_event_to_client(
                            str(client.organization.token),
                            "private",
                            "client-event",
                            pusher_data_obj_client,
                        )
                except Exception as e:
                    logger.error(
                        f"Error while sending notification to client about client status: {e}"
                    )

                # Send pusher notification about banner
                pusher_data_obj = {
                    "source_event_type": "banner_status_change",
                    "is_active": instance.is_active,
                    "banner_type": instance.banner_type,
                    "banner_id": instance.id,
                }

                publish_event_to_client(
                    str(instance.organization.token),
                    "private",
                    "client-event",
                    pusher_data_obj,
                )
            except Exception as e:
                logger.error(f"Error while sending notification to client: {e}")

        return


@receiver(pre_save, sender=Client)
def alert_client_active_status(sender, instance, **kwargs):
    if instance.pk:
        old_instance = (
            sender.objects.filter(pk=instance.pk).only("is_client_online").first()
        )
        if old_instance and old_instance.is_client_online != instance.is_client_online:

            try:
                pusher_data_obj = {
                    "source_event_type": "client_status_change",
                    "user_id": instance.user.id,
                    "is_active": instance.is_client_online,
                }

                publish_event_to_client(
                    str(instance.organization.token),
                    "private",
                    "client-event",
                    pusher_data_obj,
                )
            except Exception as e:
                logger.error(f"Error while sending notification to client: {e}")

        return


@receiver(post_save, sender=CheckInFeature)
def check_in_feature_updated(sender, instance, created, **kwargs):
    if not created:
        try:
            pusher_data_obj = {
                "source_event_type": "check_in_feature_status_change",
                "master_switch": instance.master_switch,
                "skip_switch": instance.skip_switch,
                "support_email": instance.support_email,
            }

            publish_event_to_channel(
                str(instance.organization.token),
                "private",
                "master-event",
                pusher_data_obj,
            )
        except Exception as e:
            logger.error(f"Error while sending notification to all widgets: {e}")
