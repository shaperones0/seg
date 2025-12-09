"""Segments management service."""

from collections.abc import Iterable, Mapping, Sequence
from datetime import timedelta
from typing import Annotated, Final

from asyncpg import UniqueViolationError
from fastapi import Depends

from seg.core import error
from seg.core.backoff import Backoff
from seg.db.pg import (
    PG_CONNECTION_ERRORS,
    PostgresConnection,
    get_pg,
)
from seg.model.segment import (
    User as ModelUser,
)
from seg.model.segment import (
    Users as ModelUserList,
)

REDIS_TTL: Final[timedelta] = timedelta(minutes=5)
backoff: Backoff = Backoff('User service')


class UserService:
    """Segment management service."""

    def __init__(self, db: PostgresConnection) -> None:
        """Initialize user service.

        :param db: Postgres database connection.
        """
        self.db = db

    async def user_add(self, users_ids: Iterable[int]) -> tuple[ModelUser, ...]:
        """Insert user IDs, ignore duplicate IDs.

        :param users_ids: User IDs to insert.
        :raises BackoffError: Failed to connect to Postgres.
        """
        users = tuple(ModelUser(id=uid) for uid in users_ids)
        await self._sql_user_upsert(users)
        return users

    async def user_view(
        self,
        *,
        limit: int,
        offset: int,
    ) -> ModelUserList:
        """List existing user IDs.

        :param limit: How many IDs to return.
        :param offset: How many IDs to skip.
        :return: List of IDs.
        :raises BackoffError: Failed to connect to Postgres.
        """
        return await self._sql_user_select(
            limit=limit,
            offset=offset,
        )

    async def user_delete(
        self,
        *,
        users_ids: Sequence[int],
    ) -> None:
        """Delete given IDs.

        :param users_ids: IDs to delete.
        :raises BackoffError: Failed to connect to Postgres.
        """
        await self._sql_user_delete(
            user_ids=users_ids,
        )

    async def user_update(
        self,
        *,
        ids_newids: Mapping[int, int],
    ) -> None:
        """Change user IDs.

        Change given user IDs into new ones.
        :param ids_newids: Mapping of old IDs to new IDs.
        :raises BackoffError: Failed to connect to Postgres.
        :raises UniqueError: One of the new IDs already exists.
        """
        await self._sql_user_update(
            ids_newids=ids_newids,
        )

    @backoff(
        *PG_CONNECTION_ERRORS,
        max_retries=3,
    )
    async def _sql_user_select(
        self,
        *,
        limit: int,
        offset: int,
    ) -> ModelUserList:
        """List existing user IDs.

        :param limit: How many IDs to return.
        :param offset: How many IDs to skip.
        :return: List of IDs.
        :raises BackoffError: Failed to connect to Postgres.
        """
        db_result = await self.db.fetch(
            """SELECT * FROM users
            ORDER BY id DESC
            LIMIT $1 OFFSET $2""",
            limit,
            offset,
        )
        return ModelUserList(items=tuple(ModelUser(**row) for row in db_result))

    @backoff(
        *PG_CONNECTION_ERRORS,
        max_retries=3,
    )
    async def _sql_user_upsert(self, users: Sequence[ModelUser]) -> None:
        """Insert user IDs, ignore duplicate IDs.

        :param users: Users to insert.
        :raises BackoffError: Failed to connect to Postgres.
        """
        await self.db.executemany(
            """INSERT INTO users (id)
            VALUES ($1)
            ON CONFLICT (id) DO NOTHING""",
            ((usr.id,) for usr in users),
        )

    @backoff(
        *PG_CONNECTION_ERRORS,
        max_retries=3,
    )
    async def _sql_user_delete(
        self,
        *,
        user_ids: Sequence[int],
    ) -> None:
        """Delete given IDs.

        :param user_ids: IDs to delete.
        :raises BackoffError: Failed to connect to Postgres.
        """
        await self.db.execute(
            """DELETE FROM users
            WHERE id = any($1::int[])""",
            user_ids,
        )

    @backoff(
        *PG_CONNECTION_ERRORS,
        max_retries=3,
    )
    async def _sql_user_update(
        self,
        *,
        ids_newids: Mapping[int, int],
    ) -> None:
        """Change user IDs.

        Change given user IDs into new ones.
        :param ids_newids: Mapping of old IDs to new IDs.
        :raises BackoffError: Failed to connect to Postgres.
        :raises UniqueError: One of the new IDs already exists.
        """
        try:
            async with self.db.transaction():
                await self.db.executemany(
                    """UPDATE users
                    SET id = $2
                    WHERE id = $1""",
                    ids_newids.items(),
                )
        except UniqueViolationError as exc:
            raise error.UniqueError from exc


def get_service(
    db: Annotated[PostgresConnection, Depends(get_pg)],
) -> UserService:
    """User service as a FastAPI dependency.

    :param db: Postgres database dependency.
    :return: ``UserService`` instance.
    """
    return UserService(db)
