"""Postgres connection management."""

from collections.abc import AsyncGenerator

import asyncpg
from asyncpg import Record
from asyncpg.connection import Connection

# Monkeypatch poor quality stubs
Connection.__class_getitem__ = classmethod(     # type: ignore[attr-defined]
    lambda cls, item: "Connection"
)

from seg.core.backoff import backoff

PostgresConnection = Connection[Record]     # type: ignore[attr-defined]
# Appreciate errors introduced by following best typing practices

pg_conn_info: str | None = None


async def init(postgres_connection_info: str) -> None:
    """Initialize global Postgres connection.

    :param postgres_connection_info: Postgres connection URL.
    """
    global pg_conn_info     # noqa: PLW0603 - Singleton pattern is OK
    pg_conn_info = postgres_connection_info

@backoff(
    OSError,
    max_retries=3,
    service_name="DB Connection Pool"
)
async def _connect(dsn: str) -> Connection:
    """Connect to Postgres.

    :param dsn: Postgres DSN.
    """

    return await asyncpg.connect(pg_conn_info)


async def get_pg() -> AsyncGenerator[PostgresConnection]:
    """Get the current global Postgres connection.

    Closes the connection when exiting scope.

    :returns: Postgres connection.
    """
    conn = await _connect(pg_conn_info)
    yield conn
    await conn.close()


async def close() -> None:
    """Close Postgres connection.

    No further calls to `get_connection()` may be made.
    """
    global pg_conn_info     # noqa: PLW0603 - Singleton pattern is OK
    pg_conn_info = None
