"""Segments management service."""

from collections.abc import Iterable, Mapping, Sequence
from datetime import timedelta
from typing import Annotated, Final
from uuid import UUID

from asyncpg import UniqueViolationError
from fastapi import Depends

from seg.core import error
from seg.core.backoff import backoff
from seg.db.pg import (
    PG_CONNECTION_ERRORS,
    PostgresConnection,
    get_pg,
)
from seg.db.redis import REDIS_CONNECTION_ERRORS, Redis, get_redis
from seg.model.segment import (
    Segment as ModelSegment,
)
from seg.model.segment import (
    Segments as ModelSegmentList,
)

REDIS_TTL: Final[timedelta] = timedelta(minutes=5)


class SegmentService:
    """Segment management service."""

    def __init__(self, db: PostgresConnection, redis: Redis) -> None:
        """Initialize segment management service.

        :param db: Postgres database connection.
        :param redis: Redis database connection.
        """
        self.db = db
        self.redis = redis

    async def segment_create(
        self, segments_names: Iterable[str]
    ) -> tuple[ModelSegment, ...]:
        """Create new segments by names.

        Creates new segments with names given in the array.
        Returns a list of created segments.

        Raises error if any name already exists in the database,
        aborting creation.
        :param segments_names: Names of segments to create.
        :return: Created segments.
        :raises BackoffError: Failed to connect to Postgres or Redis.
        :raises UniqueError: One or several names already exist.
        """
        segments = tuple(ModelSegment.create(name) for name in segments_names)
        await self._sql_segment_insert(segments)
        await self._redis_clear()
        return segments

    async def segments_view(
        self, *, limit: int, offset: int, name: str
    ) -> ModelSegmentList:
        """List existing segments.

        Comes with pagination and optional filtering.
        :param limit: How many segments to return.
        :param offset: How many segments to skip.
        :param name: Set to search for a segment with specific name.
        :return: List of segments found.
        :raises BackoffError: Failed to connect to Postgres or Redis.
        """
        result: ModelSegmentList
        redis_key = f'segv:{limit}:{offset}:{name}'
        redis_str: str | None = await self._redis_get(redis_key)
        if redis_str is None:
            result = await self._sql_segment_select(
                limit=limit,
                offset=offset,
                name=name,
            )
            await self._redis_set(
                redis_key, result.model_dump_json(), REDIS_TTL
            )
        else:
            result = ModelSegmentList.model_validate_json(redis_str)

        return result

    async def segments_delete(
        self,
        *,
        segments_names: Sequence[str],
        segments_ids: Sequence[UUID],
    ) -> None:
        """Delete segments by their names or IDs.

        :param segments_names: Names of segments to delete.
        :param segments_ids: IDs of segments to delete.
        :raises BackoffError: Failed to connect to Postgres or Redis.
        """
        await self._sql_segment_delete(
            segments_names=segments_names,
            segments_ids=segments_ids,
        )
        await self._redis_clear()

    async def segments_update(
        self,
        *,
        ids_names: Mapping[UUID, str],
    ) -> None:
        """Update segments names by their IDs.

        :param ids_names: Mapping of IDs to new names.
        :raises BackoffError: Failed to connect to Postgres or Redis.
        :raises UniqueError: One of the names already exists in the database.
        """
        await self._sql_segment_update(
            ids_names=ids_names,
        )
        await self._redis_clear()

    @backoff(
        *PG_CONNECTION_ERRORS,
        max_retries=3,
        service_name='Segment Service',
    )
    async def _sql_segment_select(
        self, *, limit: int, offset: int, name: str
    ) -> ModelSegmentList:
        """List existing segments.

        Comes with pagination and optional filtering.
        :param limit: How many segments to return.
        :param offset: How many segments to skip.
        :param name: Set to search for a segment with specific name.
        :return: List of segments found.
        :raises BackoffError: Failed to establish connection with Postgres.
        """
        if name:
            db_result = await self.db.fetch(
                """SELECT * FROM segments
                WHERE name = $1
                ORDER BY id DESC
                LIMIT $2 OFFSET $3""",
                name,
                limit,
                offset,
            )
        else:
            db_result = await self.db.fetch(
                """SELECT * FROM segments
                ORDER BY id DESC
                LIMIT $1 OFFSET $2""",
                limit,
                offset,
            )
        return ModelSegmentList(
            items=tuple(ModelSegment(**row) for row in db_result)
        )

    @backoff(
        *PG_CONNECTION_ERRORS,
        max_retries=3,
        service_name='Segment Service',
    )
    async def _sql_segment_insert(
        self, segments: Sequence[ModelSegment]
    ) -> None:
        """Create new segments.

        :param segments: New segment objects to create.
        :raises BackoffError: Failed to establish connection with Postgres.
        :raises UniqueError: One or several names already exist.
        """
        try:
            async with self.db.transaction():
                await self.db.executemany(
                    """INSERT INTO segments (id, name, created, modified)
                    VALUES ($1, $2, $3, $4)""",
                    (
                        (
                            segment.id,
                            segment.name,
                            segment.created,
                            segment.modified,
                        )
                        for segment in segments
                    ),
                )
        except UniqueViolationError as exc:
            raise error.UniqueError from exc

    @backoff(
        *PG_CONNECTION_ERRORS,
        max_retries=3,
        service_name='Segment Service',
    )
    async def _sql_segment_delete(
        self,
        *,
        segments_names: Sequence[str],
        segments_ids: Sequence[UUID],
    ) -> None:
        """Delete segments by their names or IDs.

        :param segments_names: Names of segments to delete.
        :param segments_ids: IDs of segments to delete.
        :raises BackoffError: Failed to establish connection with Postgres.
        """
        await self.db.execute(
            """DELETE FROM segments
            WHERE
                name = any($1::text[]) OR
                id = any($2::uuid[])""",
            segments_names,
            segments_ids,
        )

    @backoff(
        *PG_CONNECTION_ERRORS,
        max_retries=3,
        service_name='Segment Service',
    )
    async def _sql_segment_update(
        self,
        *,
        ids_names: Mapping[UUID, str],
    ) -> None:
        """Update segments names by their IDs.

        :param ids_names: Mapping of IDs to new names.
        :raises BackoffError: Failed to establish connection with Postgres.
        :raises UniqueError: One of the names already exists in the database.
        """
        try:
            async with self.db.transaction():
                await self.db.executemany(
                    """UPDATE segments
                    SET name = $2,
                        modified = (now() at time zone 'UTC')
                    WHERE id = $1""",
                    ids_names.items(),
                )
        except UniqueViolationError as exc:
            raise error.UniqueError from exc

    @backoff(
        *REDIS_CONNECTION_ERRORS,
        max_retries=3,
        service_name='Segment Service',
    )
    async def _redis_get(self, key: str) -> str | None:
        """Fetch value of a given Redis key.

        :param key: Key to look for.
        :return: Found value.
        :raises BackoffError: Failed to establish connection with Redis.
        """
        return await self._redis_get(key)

    @backoff(
        *REDIS_CONNECTION_ERRORS,
        max_retries=3,
        service_name='Segment Service',
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
        service_name='Segment Service',
    )
    async def _redis_clear(self) -> None:
        """Clears Redis database.

        :raises BackoffError: Failed to establish connection with Redis.
        """
        await self.redis.flushall()


def get_service(
    db: Annotated[PostgresConnection, Depends(get_pg)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> SegmentService:
    """Segment service as a FastAPI dependency.

    :param db: Postgres database dependency.
    :param redis: Redis database dependency.
    :return: ``SegmentService`` instance.
    """
    return SegmentService(db, redis)
