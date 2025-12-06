"""Segments management service."""

from typing import Annotated, Final
from functools import lru_cache
from collections.abc import Iterable, Sequence, Mapping
from datetime import timedelta

from fastapi import Depends
from asyncpg import ConnectionRejectionError, UniqueViolationError

from seg.core import error
from seg.core.backoff import backoff
from seg.db.pg import (
    PostgresConnection, get_pg,
    CONNECTION_ERRORS,
)
from seg.db.redis import AsyncRedis, get_redis
from seg.model.segment import (
    User as ModelUser,
    Users as ModelUserList,
)

REDIS_TTL: Final[timedelta] = timedelta(minutes=5)


class UserService:
    """Segment management service."""

    def __init__(self, db: PostgresConnection) -> None:
        self.db = db

    async def user_add(
            self,
            users_ids: Iterable[int]
    ) -> tuple[ModelUser, ...]:
        """Create users."""

        users = tuple(ModelUser(id=uid) for uid in users_ids)
        await self._sql_user_upsert(users)
        return users

    async def user_view(
            self,
            *,
            limit: int,
            offset: int,
    ) -> ModelUserList:
        """List available segments."""

        result = await self._sql_user_select(
            limit=limit,
            offset=offset,
        )
        return result

    async def user_delete(
            self,
            *,
            users_ids: Sequence[int],
    ) -> None:
        """Delete segments."""
        await self._sql_user_delete(
            user_ids=users_ids,
        )

    async def user_update(
            self,
            *,
            ids_newids: Mapping[int, int],
    ) -> None:
        """Update segments."""
        await self._sql_user_update(
            ids_newids=ids_newids,
        )

    @backoff(
        *CONNECTION_ERRORS,
        max_retries=3,
        service_name="Segment Service",
    )
    async def _sql_user_select(
            self,
            *,
            limit: int,
            offset: int,
    ) -> ModelUserList:

        db_result = await self.db.fetch(
            """SELECT * FROM users
            ORDER BY id DESC
            LIMIT $1 OFFSET $2""",
            limit, offset
        )
        return ModelUserList(
            items=tuple(ModelUser(**row) for row in db_result)
        )

    @backoff(
        *CONNECTION_ERRORS,
        max_retries=3,
        service_name="Segment Service",
    )
    async def _sql_user_upsert(
            self,
            users: Sequence[ModelUser]
    ) -> None:
        """Insert new segments."""
        await self.db.executemany(
            """INSERT INTO users (id)
            VALUES ($1)
            ON CONFLICT (id) DO NOTHING""",
            ((usr.id,) for usr in users)
        )

    @backoff(
        *CONNECTION_ERRORS,
        max_retries=3,
        service_name="Segment Service",
    )
    async def _sql_user_delete(
            self,
            *,
            user_ids: Sequence[int],
    ) -> None:
        """Delete segments."""
        await self.db.execute(
            """DELETE FROM users 
            WHERE id = any($1::int[])""",
            user_ids,
        )

    @backoff(
        *CONNECTION_ERRORS,
        max_retries=3,
        service_name="Segment Service",
    )
    async def _sql_user_update(
            self,
            *,
            ids_newids: Mapping[int, int],
    ) -> None:
        """Update segments."""
        try:
            async with self.db.transaction():
                await self.db.executemany(
                    """UPDATE users
                    SET id = $2
                    WHERE id = $1""",
                    ids_newids.items()
                )
        except UniqueViolationError as exc:
            raise error.UniqueError from exc

def get_service(
    db: Annotated[PostgresConnection, Depends(get_pg)],
) -> UserService:
    return UserService(db)
