import os
from azure.storage.blob import BlobServiceClient
from django.conf import settings

import os


def ensure_credentials_file(
    local_path="credentials.json",
    connection_string=settings.AZURE_STORAGE_CONNECTION_STRING,
    container_name="pingbase-server",
    blob_name="OAuth/google/client_secret.json",
):
    """
    Ensure the credentials file exists locally. Download from Azure Storage if it doesn't.

    :param local_path: Local filesystem path to check for the credentials file.
    :param connection_string: Azure Storage account connection string.
    :param container_name: Name of the container in the Azure Storage account.
    :param blob_name: Name of the blob (file) to download.
    :return: The path to the credentials file.
    """
    # Check if the credentials file already exists locally
    if not os.path.exists(local_path):
        # File does not exist, download it from Azure Storage
        blob_service_client = BlobServiceClient.from_connection_string(
            connection_string
        )
        container_client = blob_service_client.get_container_client(container_name)

        # Download the credentials.json file
        blob_client = container_client.get_blob_client(blob_name)
        if blob_client:
            with open(local_path, "wb") as download_file:
                download_file.write(blob_client.download_blob().readall())
            print(f"Downloaded credentials file to {local_path}")

    return local_path


def credentials_to_dict(credentials):
    return {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }
