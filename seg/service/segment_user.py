"""Segment-user relation management service."""

from collections.abc import Iterable, Sequence
from secrets import SystemRandom
from typing import Annotated, Final
from uuid import UUID

from fastapi import Depends

from seg.model import model as mdl
from seg.service import cache as svc_cache
from seg.service import db as svc_db

USER_BATCH_SIZE: Final[int] = 1000
rng = SystemRandom()


class SegmentUserService:
    """Segment-user relation management service."""

    def __init__(
        self, db: svc_db.DbService, redis: svc_cache.CacheService
    ) -> None:
        """Initialize segment-user relation management service.

        :param db: Database service.
        :param redis: Cache service
        """
        self.db = db
        self.cache = redis

    async def segusr_create(self, segusrs: Iterable[mdl.SegUsr]) -> None:
        """Create new segment-user relations.

        Existing relations are ignored.

        Resets the cache.
        :param segusrs: New segment-user objects to create.
        """
        await self.db.segusr_insert(segusrs)
        await self.cache.clear()

    async def segusr_read(
        self,
        *,
        user_ids: Sequence[int],
        segment_ids: Sequence[UUID],
        limit: int,
        offset: int,
    ) -> tuple[mdl.SegUsr, ...]:
        """List existing segment-user relations.

        Comes with pagination and optional filtering.

        Doesn't cache results. Use more specialized methods for that.
        :param user_ids: IDs of users to include. Empty for no filtering.
        :param segment_ids: IDs of segments to include. Empty for no filtering.
        :param limit: How many segments to return.
        :param offset: How many segments to skip.

        :return: List of segments found.
        """
        result = await self.db.segusr_select(
            user_ids=user_ids,
            segment_ids=segment_ids,
            limit=limit,
            offset=offset,
        )

        return result.it

    async def segusr_delete(
        self,
        *,
        user_ids: Sequence[int],
        segment_ids: Sequence[UUID],
    ) -> None:
        """Delete segments by their names or IDs.

        Resets the cache.
        :param user_ids: IDs of User to delete.
        :param segment_ids: IDs of segments to delete.
        """
        await self.db.segusr_delete(user_ids=user_ids, segment_ids=segment_ids)
        await self.cache.clear()

    async def segusr_mass(
        self,
        *,
        ratio: float,
        segment_ids: Sequence[UUID],
        subset_segment_id: UUID | None,
    ) -> None:
        """Mass assign segments to given ratio of users.

        :param ratio: Ratio between 0 and 1.
        :param segment_ids: Segments to assign.
        :param subset_segment_id: Required segment for the users.
        :raises BackoffError: Failed to connect to Postgres or Redis.
        """
        segusr_batch: list[mdl.SegUsr] = []
        async for usr in self.db.user_iter(subset_segment_id):
            if rng.random() >= ratio:
                continue
            segusr_batch.extend(
                mdl.SegUsr(seg=seg_id, usr=usr.id)
                for seg_id in segment_ids
            )
            if len(segusr_batch) >= USER_BATCH_SIZE:
                await self.db.segusr_insert(segusr_batch)
                segusr_batch.clear()
        if segusr_batch:
            await self.db.segusr_insert(segusr_batch)
        await self.cache.clear()

def get_service(
    db: Annotated[svc_db.DbService, Depends(svc_db.get_service)],
    cache: Annotated[svc_cache.CacheService, Depends(svc_cache.get_service)],
) -> SegmentUserService:
    """Segment-user relation service as a FastAPI dependency.

    :param db: Database service dependency.
    :param cache: Cache service dependency.
    :return: ``SegmentUserService`` instance.
    """
    return SegmentUserService(db, cache)
