from django.conf import settings
from azure.storage.blob import BlobServiceClient, ContentSettings
from datetime import datetime


def upload_to_azure_blob(file, prefix, blob_name) -> str:
    full_blob_name = f"{prefix}/{blob_name}"
    account_name = settings.AZURE_STORAGE_ACCOUNT_NAME
    account_key = settings.AZURE_STORAGE_ACCOUNT_KEY
    container_name = settings.AZURE_STORAGE_CONTAINER_NAME

    # Create a BlobServiceClient
    blob_service_client = BlobServiceClient(
        account_url=f"https://{account_name}.blob.core.windows.net",
        credential=account_key,
    )

    # Read the file in binary mode
    file_bytes = file.read()

    # Define the content settings with the appropriate MIME type for .webm files
    content_settings = ContentSettings(
        content_type="video/webm", content_disposition="inline"
    )

    # Create the blob from bytes
    blob_service_client.get_blob_client(
        container=container_name, blob=full_blob_name
    ).upload_blob(file_bytes, overwrite=True, content_settings=content_settings)

    # Return the blob URL
    blob_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{full_blob_name}"
    return blob_url


def convert_to_date(date_str, type=None):
    """
    Converts an ISO 8601 datetime string to a date string in YYYY-MM-DD format.

    :param date_str: ISO 8601 datetime string.
    :return: Date string in YYYY-MM-DD format.
    """
    # Check and remove the 'Z' if it's a UTC date
    if date_str.endswith("Z"):
        date_str = date_str[:-1]

    # Parse the datetime string to a datetime object

    datetime_obj = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f")

    if type == "date":
        # Format the datetime object to just the date in YYYY-MM-DD format
        return datetime_obj.strftime("%Y-%m-%d")
    else:
        return datetime_obj.strftime("%H:%M:%S")
