"""Postgres connection management."""

from collections.abc import AsyncGenerator

import psqlpy
from psqlpy import (
    Connection as DbConnection,
)
from psqlpy.exceptions import BaseConnectionPoolError

from seg.core.backoff import backoff

pg_conn_pool: psqlpy.ConnectionPool | None = None


@backoff(
    BaseConnectionPoolError,
    max_retries=3,
    service_name="DB Connection Pool",
)
async def _acquire_and_check() -> DbConnection:
    conn = pg_conn_pool.acquire()
    await conn.__aenter__()
    return conn


async def get_pg() -> AsyncGenerator[DbConnection]:
    """Get the current global Postgres connection.

    Closes the connection when exiting scope.

    :returns: Postgres connection.
    """

    async with await _acquire_and_check() as conn:
        yield conn


async def init(postgres_dsn: str) -> None:
    """Initialize global Postgres connection.

    :param postgres_dsn: Postgres connection URL.
    """
    global pg_conn_pool     # noqa: PLW0603 - Singleton pattern is OK
    pg_conn_pool = psqlpy.ConnectionPool(dsn=postgres_dsn)


async def close() -> None:
    """Close Postgres connection.

    No further calls to `get_pg()` may be made.
    """
    global pg_conn_pool     # noqa: PLW0603 - Singleton pattern is OK
    pg_conn_pool = None
