"""Management entrypoint."""

import asyncio
import logging
from collections.abc import AsyncGenerator, Callable, Coroutine
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any

import typer

from seg.core.config import SETTINGS
from seg.db import pg, redis
from seg.migrations.migrate import MigrationDict, MigrationManager

app = typer.Typer()

logger = logging.getLogger(__name__)


def coro[**T_param, T_ret](
    func: Callable[T_param, Coroutine[Any, Any, T_ret]],
) -> Callable[T_param, None]:
    """Make given async function callable from sync code.

    It's achieved by wrapping call with asyncio.run, so
    better not use it in functions that could be called
    more than once.

    :param func: Function to wrap.
    :return: Wrapped function.
    """

    @wraps(func)
    def wrapper(*args: T_param.args, **kwargs: T_param.kwargs) -> None:
        asyncio.run(func(*args, **kwargs))

    return wrapper


@asynccontextmanager
async def init_connection() -> AsyncGenerator[pg.PostgresConnection]:
    """Initialize Postgres connection.

    Closes the connection when leaving the scope.

    :returns: Postgres connection.
    """
    await pg.init(SETTINGS.pg.url)
    await redis.init(SETTINGS.redis.url)
    async for connection in pg.get_pg():
        yield connection


@app.command()
@coro
async def migrate(  # noqa: WPS210, WPS213
    fake: list[str] | None = None, *, verbose: bool = False
) -> None:
    """Migrate Postgres database."""
    if verbose:
        logger.setLevel(logging.DEBUG)

    async with init_connection() as connection:
        logger.debug('discovering migrations in standard dir...')
        migrations = MigrationDict.from_path(connection)

        manager = MigrationManager(connection)

        logger.debug('bootstrapping database if needed')
        await manager.prepare_table_if_need()

        logger.debug('reading applied migrations')
        applied = await manager.read_applied_migrations()
        logger.info('migration applied: %s', applied)

        if fake:
            logger.debug('mark faked migrations as applied')
            for fake_migration_name in fake:
                logger.info('fake migration: %s', fake_migration_name)
                applied.append(fake_migration_name)

        logger.debug('applying missing migrations')
        applied_now = await migrations.upgrade(applied)

        if fake:
            logger.debug('add faked migrations to applied_now')
            for fake_migration_name in fake:
                applied_now.append(fake_migration_name)

        logger.debug('writing migrations applied now: %s', applied_now)
        await manager.write_applied_migration(applied_now)
    logger.info('Successfully performed migrations')


if __name__ == '__main__':
    app()
