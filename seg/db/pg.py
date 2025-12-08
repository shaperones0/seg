"""Postgres connection management."""

from collections.abc import AsyncGenerator
from typing import Final

import asyncpg
from asyncpg.connection import Connection

from seg.core import error
from seg.core.backoff import backoff

# see https://github.com/MagicStack/asyncpg/issues/513
PG_CONNECTION_ERRORS: Final[error.ErrListType] = (
    OSError,
    asyncpg.CannotConnectNowError,
    asyncpg.ConnectionDoesNotExistError,
)

# Monkeypatch poor quality stubs
Connection.__class_getitem__ = classmethod(  # type: ignore[attr-defined]
    lambda cls, item: 'Connection'  # noqa: WPS117, WPS110
)

PostgresConnection = Connection[asyncpg.Record]

pg_conn_info: str | None = None


async def init(postgres_connection_info: str) -> None:
    """Initialize global Postgres connection.

    :param postgres_connection_info: Postgres connection URL.
    """
    global pg_conn_info  # noqa: PLW0603, WPS420
    pg_conn_info = postgres_connection_info


@backoff(
    *PG_CONNECTION_ERRORS, max_retries=3, service_name='DB Connection Pool'
)
async def _connect() -> Connection:
    """Connect to Postgres.

    Function does exponential backoff.
    :return: Connection.
    """
    return await asyncpg.connect(pg_conn_info)


async def get_pg() -> AsyncGenerator[PostgresConnection]:
    """Get the current global Postgres connection.

    Closes the connection when exiting scope.

    :returns: Postgres connection.
    """
    conn = await _connect()
    yield conn
    await conn.close()


async def close() -> None:
    """Close Postgres connection.

    No further calls to `get_connection()` may be made.
    """
    global pg_conn_info  # noqa: PLW0603, WPS420 - Singleton pattern is OK
    pg_conn_info = None
