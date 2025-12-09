"""Segment-user relation management service."""

from collections.abc import Sequence
from datetime import timedelta
from typing import Annotated, Final, cast
from uuid import UUID

from fastapi import Depends

from seg.core.backoff import Backoff
from seg.db.pg import (
    PG_CONNECTION_ERRORS,
    PostgresConnection,
    get_pg,
)
from seg.db.redis import REDIS_CONNECTION_ERRORS, Redis, get_redis
from seg.model.segment import SegmentUser as ModelSegmentUser
from seg.model.segment import (
    SegmentUserList as ModelSegmentUserList,
)

REDIS_TTL: Final[timedelta] = timedelta(minutes=5)
backoff: Backoff = Backoff('Segment-user service')


class SegmentUserService:
    """Segment-user relation management service."""

    def __init__(self, db: PostgresConnection, redis: Redis) -> None:
        """Initialize segment management service.

        :param db: Postgres database connection.
        :param redis: Redis database connection.
        """
        self.db = db
        self.redis = redis

    async def su_create(self, sus: Sequence[ModelSegmentUser]) -> None:
        """Create new segment-user relations.

        Existing relations are ignored.

        Resets the cache.
        :param sus: New segment-user objects to create.
        :raises BackoffError: Failed to establish connection with Postgres.
        """
        await self._sql_su_insert(sus)
        await self._redis_clear()

    async def su_view(
        self,
        *,
        user_ids: Sequence[int],
        segment_ids: Sequence[UUID],
        limit: int,
        offset: int,
    ) -> ModelSegmentUserList:
        """List existing segment-user relations.

        Comes with pagination and optional filtering.

        Results are cached only if requested only one user ID or
        only one segment ID.
        :param user_ids: IDs of users to include. Empty for no filtering.
        :param segment_ids: IDs of segments to include. Empty for no filtering.
        :param limit: How many segments to return.
        :param offset: How many segments to skip.

        :return: List of segments found.
        :raises BackoffError: Failed to connect to Postgres or Redis.
        """
        result: ModelSegmentUserList | None = None
        redis_key = ''
        if len(user_ids) == 1 and len(segment_ids) == 0:
            # Cache user query
            redis_key = f'suu:{user_ids[0]}:{limit}:{offset}'
        elif len(user_ids) == 0 and len(segment_ids) == 1:
            # Cache segment query
            redis_key = f'sus:{segment_ids[0]}:{limit}:{offset}'

        if redis_key:
            redis_str = await self._redis_get(redis_key)
            if redis_str is not None:
                result = ModelSegmentUserList.model_validate_json(redis_str)

        if result is None:
            # Get from database
            result = await self._sql_su_select(
                user_ids=user_ids,
                segment_ids=segment_ids,
                limit=limit,
                offset=offset,
            )

        # Write into Redis if applicable
        if redis_key:
            redis_str = result.model_dump_json()
            await self._redis_set(redis_key, redis_str, REDIS_TTL)

        return result

    async def su_delete(
        self,
        *,
        user_ids: Sequence[int],
        segment_ids: Sequence[UUID],
    ) -> None:
        """Delete segments by their names or IDs.

        Resets the cache.
        :param user_ids: IDs of User to delete.
        :param segment_ids: IDs of segments to delete.
        :raises BackoffError: Failed to connect to Postgres or Redis.
        """
        await self._sql_su_delete(
            user_ids=user_ids,
            segment_ids=segment_ids,
        )
        await self._redis_clear()

    @backoff(
        *PG_CONNECTION_ERRORS,
        max_retries=3,
    )
    async def _sql_su_select(
        self,
        *,
        user_ids: Sequence[int],
        segment_ids: Sequence[UUID],
        limit: int,
        offset: int,
    ) -> ModelSegmentUserList:
        """List existing segment-user relations.

        Comes with pagination and optional filtering.
        Results are not cached.
        :param user_ids: IDs of users to include. Empty for no filtering.
        :param segment_ids: IDs of segments to include. Empty for no filtering.
        :param limit: How many segments to return.
        :param offset: How many segments to skip.

        :return: List of segments found.
        :raises BackoffError: Failed to connect to Postgres or Redis.
        """
        if user_ids and segment_ids:
            db_result = await self.db.fetch(
                """SELECT *
                FROM segment_user
                WHERE
                    usr = any($1::int[]) AND
                    seg = any($2::uuid[])
                ORDER BY usr DESC
                LIMIT $3 OFFSET $4""",
                user_ids,
                segment_ids,
                limit,
                offset,
            )
        elif user_ids:
            db_result = await self.db.fetch(
                """SELECT *
                   FROM segment_user
                   WHERE usr = any ($1::int[])
                   ORDER BY usr DESC
                   LIMIT $2 OFFSET $3""",
                user_ids,
                limit,
                offset,
            )
        elif segment_ids:
            db_result = await self.db.fetch(
                """SELECT *
                   FROM segment_user
                   WHERE seg = any ($1::uuid[])
                   ORDER BY usr DESC
                   LIMIT $2 OFFSET $3""",
                segment_ids,
                limit,
                offset,
            )
        else:
            db_result = await self.db.fetch(
                """SELECT *
                   FROM segment_user
                   ORDER BY usr DESC
                   LIMIT $1 OFFSET $2""",
                limit,
                offset,
            )

        # Intentionally leave this as **, to make sure models are updated
        #  when database updates - pydantic will point which fields
        #  aren't updated in the model
        return ModelSegmentUserList(
            items=tuple(ModelSegmentUser(**row) for row in db_result)
        )

    @backoff(
        *PG_CONNECTION_ERRORS,
        max_retries=3,
    )
    async def _sql_su_insert(self, sus: Sequence[ModelSegmentUser]) -> None:
        """Create new segment-user relations.

        Existing relations are ignored.
        :param sus: New segment-user objects to create.
        :raises BackoffError: Failed to establish connection with Postgres.
        """
        await self.db.executemany(
            'INSERT INTO segment_user (seg, usr) VALUES ($1, $2)',
            ((su.segment, su.user) for su in sus),
        )

    @backoff(
        *PG_CONNECTION_ERRORS,
        max_retries=3,
    )
    async def _sql_su_delete(
        self,
        *,
        user_ids: Sequence[int],
        segment_ids: Sequence[UUID],
    ) -> None:
        """Delete segment-user relations by IDs of users or segments.

        :param user_ids: IDs of users to delete.
        :param segment_ids: IDs of segments to delete.
        :raises BackoffError: Failed to establish connection with Postgres.
        """
        if user_ids and segment_ids:
            await self.db.execute(
                """DELETE
                FROM segment_user
                WHERE
                    usr = any($1::int[]) AND
                    seg = any($2::uuid[])""",
                user_ids,
                segment_ids,
            )
        elif user_ids:
            await self.db.execute(
                """DELETE
                FROM segment_user
                WHERE usr = any($1::int[])""",
                user_ids,
            )
        elif segment_ids:
            await self.db.execute(
                """DELETE
                   FROM segment_user
                   WHERE seg = any($1::uuid[])""",
                segment_ids,
            )

    @backoff(
        *REDIS_CONNECTION_ERRORS,
        max_retries=3,
    )
    async def _redis_get(self, key: str) -> str | None:
        """Fetch value of a given Redis key.

        :param key: Key to look for.
        :return: Found value.
        :raises BackoffError: Failed to establish connection with Redis.
        """
        return cast(str, await self.redis.get(key))

    @backoff(
        *REDIS_CONNECTION_ERRORS,
        max_retries=3,
    )
    async def _redis_set(self, key: str, value: str, expire: timedelta) -> None:  # noqa: WPS110
        """Creates/modifies new value in Redis with provided expiration time.

        :param key: Key to create / modify.
        :param value: Value to set to given key.
        :param expire: Time until the key is expired.
        :raises BackoffError: Failed to establish connection with Redis.
        """
        await self.redis.set(key, value, ex=expire)

    @backoff(
        *REDIS_CONNECTION_ERRORS,
        max_retries=3,
    )
    async def _redis_clear(self) -> None:
        """Clears Redis database.

        :raises BackoffError: Failed to establish connection with Redis.
        """
        await self.redis.flushall()


def get_service(
    db: Annotated[PostgresConnection, Depends(get_pg)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> SegmentUserService:
    """Segment-user relation service as a FastAPI dependency.

    :param db: Postgres database dependency.
    :param redis: Redis database dependency.
    :return: ``SegmentUserService`` instance.
    """
    return SegmentUserService(db, redis)
