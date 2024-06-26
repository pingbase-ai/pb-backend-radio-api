from django.conf import settings
from azure.storage.blob import BlobServiceClient, ContentSettings
from datetime import datetime
from infra_utils.utils import encode_base64

import requests
import logging
import ffmpeg

logger = logging.getLogger("django")


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
    # Create the blob from bytes
    blob_service_client.get_blob_client(
        container=container_name, blob=full_blob_name
    ).upload_blob(file, overwrite=True, blob_type="BlockBlob")

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


def fetch_session_id_from_dyte(meeting_id: str) -> str:
    """
    Fetches the session ID from Dyte for a given meeting ID.

    :param meeting_id: Dyte meeting ID.
    :return: Dyte session ID.
    """
    base_url = settings.DYTE_BASE_URL
    api_key = settings.DYTE_API_KEY
    org_id = settings.DYTE_ORG_ID
    end_point = f"{base_url}/meetings/{meeting_id}/active-session"

    encoded_token = encode_base64(f"{org_id}:{api_key}")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {encoded_token}",
    }

    try:
        response = requests.get(end_point, headers=headers)
        data = response.json()
        logger.info("data", data)
        session_id = data.get("data").get("id")
        return session_id
    except Exception as e:
        logger.error(f"Error while fetching session ID from Dyte: {e}")
        return ""


def convert_webm_to_mp3(input_file, output_filename):
    """
    Converts a WebM file to MP3 using ffmpeg-python.
    Reads from an input file object and writes the result to a specified output file.
    """
    try:
        # Setup input stream from the file buffer
        input_stream = ffmpeg.input("pipe:0", format="webm")

        # Setup output stream to save the file directly
        output_stream = ffmpeg.output(input_stream, "pipe:1", format="mp3")

        # Process the streams
        process = (
            ffmpeg.input("pipe:0", format="webm")
            .output("pipe:1", format="mp3")
            .run_async(pipe_stdin=True, pipe_stdout=True, pipe_stderr=True)
        )

        # Send input file data and receive output file data
        output, _ = process.communicate(input=input_file.read())

        # Write the output to the specified file
        with open(output_filename, "wb") as f:
            f.write(output)
        return output_filename
    except ffmpeg.Error as e:
        logger.error(f"An error occurred: {e.stderr}")
        raise e
