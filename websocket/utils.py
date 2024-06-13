from redis.asyncio import Redis
from django.conf import settings


class RedisPool:
    _instance = None

    @classmethod
    async def get_instance(cls):
        if cls._instance is None:
            cls._instance = Redis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
            )
        return cls._instance
