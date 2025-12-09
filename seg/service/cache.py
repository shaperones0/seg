"""Cache service."""

from datetime import timedelta
from typing import Annotated, Final, cast

from fastapi import Depends

from seg.core import backoff as bo
from seg.db import redis

REDIS_TTL: Final[timedelta] = timedelta(minutes=5)

backoff = bo.Backoff(service_name='Cache service')


class CacheService:
    """Cache interface service.

    Provides backoff layer.
    """

    def __init__(self, conn: redis.Redis) -> None:
        """Initialize database interface service.

        :param conn: Database connection
        """
        self.redis = conn

    @backoff(
        *redis.REDIS_CONNECTION_ERRORS,
        max_retries=3,
    )
    async def get(self, key: str) -> str | None:
        """Fetch value of a given Redis key.

        :param key: Key to look for.
        :return: Found value.
        :raises BackoffError: Failed to establish connection with Redis.
        """
        return cast(str, await self.redis.get(key))

    @backoff(
        *redis.REDIS_CONNECTION_ERRORS,
        max_retries=3,
    )
    async def set(
        self,
        key: str,
        value: str,  # noqa: WPS110
        expire: timedelta | None = None,
    ) -> None:
        """Creates/modifies new value in Redis with provided expiration time.

        :param key: Key to create / modify.
        :param value: Value to set to given key.
        :param expire: Time until the key is expired.
        :raises BackoffError: Failed to establish connection with Redis.
        """
        await self.redis.set(key, value, ex=expire or REDIS_TTL)

    @backoff(
        *redis.REDIS_CONNECTION_ERRORS,
        max_retries=3,
    )
    async def clear(self) -> None:
        """Clears Redis database.

        :raises BackoffError: Failed to establish connection with Redis.
        """
        await self.redis.flushall()


def get_service(
    cache: Annotated[redis.Redis, Depends(redis.get_redis)],
) -> CacheService:
    """Service factory as a FastAPI dependency.

    :param cache: Cache connection.
    :returns: ``CacheService`` instance.
    """
    return CacheService(cache)
