"""Postgres connection management."""

from collections.abc import AsyncGenerator

import psqlpy
from psqlpy import Connection as DbConnection

pg_conn_pool: psqlpy.ConnectionPool | None = None


async def get_pg() -> AsyncGenerator[DbConnection]:
    """Get the current global Postgres connection.

    Closes the connection when exiting scope.

    :returns: Postgres connection.
    """
    async with pg_conn_pool.acquire() as conn:
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
