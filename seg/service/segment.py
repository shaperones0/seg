"""Segments management service."""

from typing import Annotated
from functools import lru_cache
from collections.abc import Iterable, Sequence
from uuid import UUID
from datetime import timedelta

from fastapi import Depends
from asyncpg import ConnectionRejectionError

from seg.core import error
from seg.core.backoff import backoff
from seg.db.pg import Connection, get_pg
from seg.db.redis import AsyncRedis, get_redis
from seg.model.segment import (
    Segment as ModelSegment,
    SegmentList as ModelSegmentList,
    SegmentUser as ModelSegmentUser,
)

REDIS_TTL = timedelta(minutes=5)


class SegmentService:
    """Segment management service."""

    def __init__(self, db: Connection, redis: AsyncRedis) -> None:
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
            like: str
    ) -> ModelSegmentList:
        """List available segments."""

        result: ModelSegmentList
        key = f"segv:{limit}:{offset}:{like}"
        redis_str: str | None = await self.redis.get(key)
        if redis_str is None:
            result = await self._sql_segment_select(
                limit=limit,
                offset=offset,
                like=like,
            )
            await self.redis.set(key, result.model_dump_json(), ex=REDIS_TTL)
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

    @backoff(
        OSError,
        max_retries=3,
        service_name="Segment Service",
    )
    async def _sql_segment_select(
            self,
            *,
            limit: int,
            offset: int,
            like: str
    ) -> ModelSegmentList:
        if like:
            db_result = await self.db.fetch(
                "SELECT * FROM segments "
                "WHERE name LIKE '%$1%' "
                "ORDER BY id DESC "
                "LIMIT $2 OFFSET $3",
                like, limit, offset
            )
        else:
            db_result = await self.db.fetch(
                "SELECT * FROM segments "
                "ORDER BY id DESC "
                "LIMIT $1 OFFSET $2",
                limit, offset
            )
        return ModelSegmentList(
            items=[ModelSegment(**row) for row in db_result]
        )

    @backoff(
        OSError,
        max_retries=3,
        service_name="Segment Service",
    )
    async def _sql_segment_insert(
            self,
            segments: Sequence[ModelSegment]
    ) -> None:
        """Insert new segments."""
        await self.db.executemany(
            "INSERT INTO segments (id, name, created, modified) "
            "VALUES ($1, $2, $3, $4)",
            [[
                segment.id,
                segment.name,
                segment.created,
                segment.modified
            ] for segment in segments]
        )
        await self.redis.flushall()

    async def _sql_segment_delete(
            self,
            *,
            segments_names: Sequence[str],
            segments_ids: Sequence[UUID],
    ) -> None:
        """Delete segments."""
        await self.db.execute(
            "DELETE FROM segments WHERE name = any($1::text[]) OR id = any($2::uuid[])",
            tuple(segments_names), tuple(segments_ids)
        )


def get_service(
    db: Annotated[Connection, Depends(get_pg)],
    redis: Annotated[AsyncRedis, Depends(get_redis)],
) -> SegmentService:
    return SegmentService(db, redis)
