"""Redis connection management."""

from typing import Final
from urllib.parse import parse_qs, urlparse

from redis.asyncio import ConnectionError as RedisConnectionError
from redis.asyncio import Redis as Redis

from seg.core import error
from seg.core import type as typ
from seg.core.backoff import backoff

redis_cache: Redis | None = None

REDIS_CONNECTION_ERRORS: Final[error.ErrListType] = (RedisConnectionError,)


def get_redis() -> Redis:
    """Redis connection factory.

    :returns: Redis instance.
    """
    if redis_cache is None:
        raise RuntimeError('Redis is not configured')
    return redis_cache


@backoff(
    *REDIS_CONNECTION_ERRORS, max_retries=3, service_name='DB Connection Pool'
)
async def _connect(
    *,
    host: str,
    port: int,
    db: int,
    username: str | None = None,
    password: str | None = None,
) -> Redis:
    """Connect to Redis with backoff.

    :param host: Redis host.
    :param port: Redis port.
    :param db: Redis DB.
    :param username: Redis username.
    :param password: Redis password.
    :return: Redis connection.
    """
    # test run
    client = Redis(
        host=host,
        port=port,
        db=db,
        username=username,
        password=password,
        encoding='utf-8',
        decode_responses=True,
        socket_connect_timeout=1,
    )
    await client.ping()  # type: ignore[misc]
    await client.aclose()

    return Redis(
        host=host,
        port=port,
        db=db,
        username=username,
        password=password,
        encoding='utf-8',
        decode_responses=True,
    )


async def init(url: str) -> None:
    """Initialize global Redis connection.

    :param url: Redis connection URL.
    """
    global redis_cache  # noqa: PLW0603, WPS420 - Singleton pattern is OK
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    redis_cache = await _connect(
        host=typ.scast(str, parsed.hostname),
        port=typ.scast(int, parsed.port),
        db=int(query.get('db', [0])[0]),
        username=parsed.username,
        password=parsed.password,
    )


async def close() -> None:
    """Closes Redis connection.

    No further calls to `get_redis()` may be made.
    """
    global redis_cache  # noqa: PLW0603, WPS420 - Singleton pattern is OK
    if not isinstance(redis_cache, Redis):
        raise TypeError('Redis is not configured')

    await redis_cache.aclose()
    redis_cache = None
