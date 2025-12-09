"""Segments management service."""

from collections.abc import Iterable, Mapping, Sequence
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from seg.model import model as mdl
from seg.service import cache as svc_cache
from seg.service import db as svc_db


class SegmentService:
    """Segment management service."""

    def __init__(
        self, db: svc_db.DbService, redis: svc_cache.CacheService
    ) -> None:
        """Initialize segment management service.

        :param db: Database service.
        :param redis: Cache service
        """
        self.db = db
        self.cache = redis

    async def segment_create(
        self, segments_names: Iterable[str]
    ) -> tuple[mdl.Segment, ...]:
        """Create new segments by names.

        Creates new segments with names given in the array.
        Returns a list of created segments.

        Raises error if any name already exists in the database,
        aborting creation.

        Resets the cache.
        :param segments_names: Names of segments to create.
        :return: Created segments.
        :raises UniqueError: One or several names already exist.
        """
        segments = tuple(mdl.Segment.create(name) for name in segments_names)
        await self.db.segment_insert(segments)
        await self.cache.clear()
        return segments

    async def segment_read(
        self, *, limit: int, offset: int, name: str, user_id: int | None
    ) -> tuple[mdl.Segment, ...]:
        """List existing segments.

        Comes with pagination and optional filtering.

        Results are cached.
        :param limit: How many segments to return.
        :param offset: How many segments to skip.
        :param name: Set to search for a segment with specific name.
        :param user_id: Set to only display segments of given user.
        :return: List of segments found.
        """
        redis_key = f's:{limit}:{offset}:{name}:{user_id}'
        redis_str = await self.cache.get(redis_key)
        if redis_str is None:
            result = await self.db.segment_select(
                limit=limit,
                offset=offset,
                name=name,
                user_id=user_id,
            )
            redis_str = result.model_dump_json()
            await self.cache.set(redis_key, redis_str)
        else:
            result = mdl.List[mdl.Segment].model_validate_json(redis_str)

        return result.it

    async def segment_update(self, ids_names: Mapping[UUID, str]) -> None:
        """Update segments names by their IDs.

        Resets the cache.
        :param ids_names: Mapping of IDs to new names.
        :raises UniqueError: One of the names already exists in the database.
        """
        await self.db.segment_update(ids_names)
        await self.cache.clear()

    async def segment_delete(
        self,
        *,
        segments_names: Sequence[str],
        segments_ids: Sequence[UUID],
    ) -> None:
        """Delete segments by their names or IDs.

        Resets the cache.
        :param segments_names: Names of segments to delete.
        :param segments_ids: IDs of segments to delete.
        """
        await self.db.segment_delete(
            segments_names=segments_names,
            segments_ids=segments_ids,
        )
        await self.cache.clear()


def get_service(
    db: Annotated[svc_db.DbService, Depends(svc_db.get_service)],
    cache: Annotated[svc_cache.CacheService, Depends(svc_cache.get_service)],
) -> SegmentService:
    """Segment service as a FastAPI dependency.

    :param db: Database service dependency.
    :param cache: Cache service dependency.
    :return: ``SegmentService`` instance.
    """
    return SegmentService(db, cache)
