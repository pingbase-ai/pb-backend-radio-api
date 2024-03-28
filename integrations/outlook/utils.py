import msal
from django.conf import settings

# MSAL configuration
CLIENT_ID = settings.AZURE_PINGBASE_APP_CLIENT_ID
CLIENT_SECRET = settings.AZURE_PINGBASE_APP_CLIENT_SECRET_VALUE
AUTHORITY = "https://login.microsoftonline.com/" + settings.AZURE_PINGBASE_APP_TENANT_ID


def build_msal_app(cache=None):
    return msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
        token_cache=cache,
    )
