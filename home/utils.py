from azure.storage.blob import BlobServiceClient
from django.conf import settings


def upload_to_azure_blob(file, prefix, blob_name) -> str:

    full_blob_name = f"{prefix}/{blob_name}"
    # Get your Azure account details
    account_name = settings.AZURE_STORAGE_ACCOUNT_NAME
    account_key = settings.AZURE_STORAGE_ACCOUNT_KEY
    container_name = settings.AZURE_STORAGE_CONTAINER_NAME

    # Create a BlobServiceClient
    blob_service_client = BlobServiceClient(
        account_url=f"https://{account_name}.blob.core.windows.net",
        credential=account_key,
    )

    # Get the container client
    # container_client = blob_service_client.get_container_client()

    # # Create the container if it doesn't exist
    # container_client.create_container()

    # Create a blob client using the local file name as the name for the blob
    blob_client = blob_service_client.get_blob_client(
        container=container_name, blob=full_blob_name
    )

    # Upload the file
    blob_client.upload_blob(file)

    # Return the blob URL
    return blob_client.url
