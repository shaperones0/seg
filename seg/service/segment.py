"""Segments management service."""

from typing import Annotated
from functools import lru_cache
from collections.abc import Iterable, Sequence
from uuid import UUID

from fastapi import Depends

from seg.core import error
from seg.db.pg import DbConnection, get_pg
from seg.db.redis import AsyncRedis, get_redis
from seg.model.segment import (
    Segment as ModelSegment,
    SegmentUser as ModelSegmentUser,
)


class SegmentService:
    """Segment management service."""

    def __init__(self, db: DbConnection, redis: AsyncRedis) -> None:
        self.db = db
        self.redis = redis

    async def segment_create(
            self,
            segments_names: Iterable[str]
    ) -> tuple[ModelSegment, ...]:
        """Create a new segment."""

        segments = tuple(ModelSegment.create(name) for name in segments_names)
        await self._sql_segment_insert(segments)
        return segments

    async def segments_view(
            self,
            *,
            limit: int,
            offset: int,
            like: str
    ) -> list[ModelSegment]:
        """List available segments."""

        if like:
            results = await self.db.fetch(
                "SELECT * FROM segments "
                "WHERE name LIKE '%$1%' "
                "ORDER BY id DESC "
                "LIMIT $2 OFFSET $3",
                (like, limit, offset)
            )
        else:
            results = await self.db.fetch(
                "SELECT * FROM segments "
                "ORDER BY id DESC "
                "LIMIT $1 OFFSET $2",
                (limit, offset)
            )

        return [ModelSegment(**row) for row in results.result()]

    async def _sql_segment_insert(
            self,
            segments: Sequence[ModelSegment]
    ) -> None:
        """Insert new segments."""
        await self.db.execute_many(
            "INSERT INTO segments (id, name, created, modified) "
            "VALUES ($1, $2, $3, $4)",
            [[
                segment.id,
                segment.name,
                segment.created,
                segment.modified
            ] for segment in segments]
        )


def get_service(
    db: Annotated[DbConnection, Depends(get_pg)],
    redis: Annotated[AsyncRedis, Depends(get_redis)],
) -> SegmentService:
    return SegmentService(db, redis)