"""Redis connection management."""

from urllib.parse import parse_qs, urlparse

from redis.asyncio import Redis as AsyncRedis

redis_cache: AsyncRedis | None = None


def get_redis_cache() -> AsyncRedis:
    """Redis connection factory.

    :returns: AsyncRedis instance.
    """
    if redis_cache is None:
        raise RuntimeError("Redis is not configured")
    return redis_cache


async def init(url: str) -> None:
    """Initialize global Redis connection.

    :param url: Redis connection URL.
    """
    global redis_cache    # noqa: PLW0603 - Singleton pattern is OK
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    dsn = {
        "host": parsed.hostname,
        "port": parsed.port,
        "db": query.get("db", [0])[0],
    }

    if parsed.username:
        dsn["username"] = parsed.username
    if parsed.password:
        dsn["password"] = parsed.password

    redis_cache = AsyncRedis(
        **dsn,
        encoding="utf-8",
        decode_responses=True
    )


async def close() -> None:
    """Closes Redis connection.

    No further calls to `get_redis()` may be made.
    """
    if not isinstance(redis_cache, AsyncRedis):
        raise TypeError("Redis is not configured")

    await redis_cache.close()
