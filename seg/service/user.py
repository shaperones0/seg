"""User management service."""

from collections.abc import Iterable, Mapping, Sequence
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from seg.model import model as mdl
from seg.service import cache as svc_cache
from seg.service import db as svc_db


class UserService:
    """User management service."""

    def __init__(
        self, db: svc_db.DbService, redis: svc_cache.CacheService
    ) -> None:
        """Initialize user management service.

        :param db: Database service.
        :param redis: Cache service
        """
        self.db = db
        self.cache = redis

    async def user_add(self, users_ids: Iterable[int]) -> None:
        """Insert user IDs, ignore duplicate IDs.

        Resets the cache.
        :param users_ids: User IDs to insert.
        """
        await self.db.user_upsert(users_ids)
        await self.cache.clear()

    async def user_read(
        self, *, limit: int, offset: int, segment_id: UUID | None
    ) -> tuple[int, ...]:
        """List existing user IDs.

        Result is cached.
        :param limit: How many IDs to return.
        :param offset: How many IDs to skip.
        :param segment_id: Set to list users in this segment.
        :return: List of IDs.
        """
        redis_key = f'u:{limit}:{offset}:{segment_id}'
        redis_str = await self.cache.get(redis_key)
        if redis_str is None:
            result = await self.db.user_select(
                limit=limit,
                offset=offset,
                segment_id=segment_id,
            )
            redis_str = result.model_dump_json()
            await self.cache.set(redis_key, redis_str)
        else:
            result = mdl.List[mdl.User].model_validate_json(redis_str)

        return tuple(user.id for user in result.it)

    async def user_delete(self, user_ids: Sequence[int]) -> None:
        """Delete given IDs.

        Resets the cache.
        :param user_ids: IDs to delete.
        """
        await self.db.user_delete(user_ids)
        await self.cache.clear()

    async def user_update(self, ids_newids: Mapping[int, int]) -> None:
        """Change user IDs.

        Change given user IDs into new ones.

        Resets the cache.
        :param ids_newids: Mapping of old IDs to new IDs.
        :raises UniqueError: One of the new IDs already exists.
        """
        await self.db.user_update(ids_newids)
        await self.cache.clear()


def get_service(
    db: Annotated[svc_db.DbService, Depends(svc_db.get_service)],
    cache: Annotated[svc_cache.CacheService, Depends(svc_cache.get_service)],
) -> UserService:
    """User service as a FastAPI dependency.

    :param db: Database service dependency.
    :param cache: Cache service dependency.
    :return: ``UserService`` instance.
    """
    return UserService(db, cache)
