"""Segments management service."""

from typing import Annotated, Final
from functools import lru_cache
from collections.abc import Iterable, Sequence, Mapping
from uuid import UUID
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
    Segment as ModelSegment,
    Segments as ModelSegmentList,
    SegmentUser as ModelSegmentUser,
)

REDIS_TTL: Final[timedelta] = timedelta(minutes=5)


class SegmentService:
    """Segment management service."""

    def __init__(self, db: PostgresConnection, redis: AsyncRedis) -> None:
        self.db = db
        self.redis = redis

    async def segment_create(
            self,
            segments_names: Iterable[str]
    ) -> tuple[ModelSegment, ...]:
        """Create a new segment."""

        segments = tuple(ModelSegment.create(name) for name in segments_names)
        await self._sql_segment_insert(segments)
        await self.redis.flushall()
        return segments

    async def segments_view(
            self,
            *,
            limit: int,
            offset: int,
            name: str
    ) -> ModelSegmentList:
        """List available segments."""

        result: ModelSegmentList
        redis_key = f"segv:{limit}:{offset}:{name}"
        redis_str: str | None = await self.redis.get(redis_key)
        if redis_str is None:
            result = await self._sql_segment_select(
                limit=limit,
                offset=offset,
                name=name,
            )
            await self.redis.set(
                redis_key,
                result.model_dump_json(),
                ex=REDIS_TTL
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
        """Delete segments."""
        await self._sql_segment_delete(
            segments_names=segments_names,
            segments_ids=segments_ids,
        )
        await self.redis.flushall()

    async def segments_update(
            self,
            *,
            ids_names: Mapping[UUID, str],
    ) -> None:
        """Update segments."""
        await self._sql_segment_update(
            ids_names=ids_names,
        )
        await self.redis.flushall()

    @backoff(
        *CONNECTION_ERRORS,
        max_retries=3,
        service_name="Segment Service",
    )
    async def _sql_segment_select(
            self,
            *,
            limit: int,
            offset: int,
            name: str
    ) -> ModelSegmentList:
        if name:
            db_result = await self.db.fetch(
                """SELECT * FROM segments
                WHERE name = $1
                ORDER BY id DESC
                LIMIT $2 OFFSET $3""",
                name, limit, offset
            )
        else:
            db_result = await self.db.fetch(
                """SELECT * FROM segments
                ORDER BY id DESC
                LIMIT $1 OFFSET $2""",
                limit, offset
            )
        return ModelSegmentList(
            items=tuple(ModelSegment(**row) for row in db_result)
        )

    @backoff(
        *CONNECTION_ERRORS,
        max_retries=3,
        service_name="Segment Service",
    )
    async def _sql_segment_insert(
            self,
            segments: Sequence[ModelSegment]
    ) -> None:
        """Insert new segments."""

        try:
            async with self.db.transaction():
                await self.db.executemany(
                    """INSERT INTO segments (id, name, created, modified)
                    VALUES ($1, $2, $3, $4)""",
                    ((
                        segment.id,
                        segment.name,
                        segment.created,
                        segment.modified
                    ) for segment in segments)
                )
        except UniqueViolationError as exc:
            raise error.UniqueError from exc

    @backoff(
        *CONNECTION_ERRORS,
        max_retries=3,
        service_name="Segment Service",
    )
    async def _sql_segment_delete(
            self,
            *,
            segments_names: Sequence[str],
            segments_ids: Sequence[UUID],
    ) -> None:
        """Delete segments."""
        await self.db.execute(
            """DELETE FROM segments 
            WHERE 
                name = any($1::text[]) OR 
                id = any($2::uuid[])""",
            segments_names, segments_ids
        )

    @backoff(
        *CONNECTION_ERRORS,
        max_retries=3,
        service_name="Segment Service",
    )
    async def _sql_segment_update(
            self,
            *,
            ids_names: Mapping[UUID, str],
    ) -> None:
        """Update segments."""
        try:
            async with self.db.transaction():
                await self.db.executemany(
                    """UPDATE segments
                    SET name = $2,
                        modified = (now() at time zone 'UTC')
                    WHERE id = $1""",
                    ids_names.items()
                )
        except UniqueViolationError as exc:
            raise error.UniqueError from exc

def get_service(
    db: Annotated[PostgresConnection, Depends(get_pg)],
    redis: Annotated[AsyncRedis, Depends(get_redis)],
) -> SegmentService:
    return SegmentService(db, redis)
