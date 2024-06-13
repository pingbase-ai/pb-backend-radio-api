from channels.middleware import BaseMiddleware
from channels.auth import AuthMiddlewareStack
from channels.db import DatabaseSyncToAsync
from urllib.parse import parse_qs


@DatabaseSyncToAsync
def get_organization_by_token(token):
    from user.models import Organization

    try:
        return Organization.objects.get(token=token)
    except Organization.DoesNotExist:
        return None


class TokenAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):

        query_string = parse_qs(scope["query_string"].decode())
        token = query_string.get("token", [None])[0]

        if not token:
            # decline the connection
            await send(
                {
                    "type": "websocket.close",
                    "code": 403,
                    "reason": "Invalid or missing token",
                }
            )
            return

        # Validate token
        org = await get_organization_by_token(token)
        if not org:
            await send(
                {
                    "type": "websocket.close",
                    "code": 403,
                    "reason": "Invalid token",
                }
            )
            return

        scope["organization"] = org

        return await super().__call__(scope, receive, send)


def TokenAuthMiddlewareStack(inner):
    return TokenAuthMiddleware(AuthMiddlewareStack(inner))
