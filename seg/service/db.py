"""Database service."""

from collections.abc import AsyncIterator, Iterable, Mapping, Sequence
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from seg.core import backoff as bo
from seg.core import error
from seg.db import pg
from seg.model import model as mdl

backoff = bo.Backoff(service_name='Database service')


class DbService:
    """Database interface service.

    Acts as a layer between logic services and database,
    uses Pydantic models and turns them into queries.
    """

    def __init__(self, conn: pg.PostgresConnection) -> None:
        """Initialize database interface service.

        :param conn: Database connection
        """
        self.pg = conn

    @backoff(
        *pg.PG_CONNECTION_ERRORS,
        max_retries=3,
    )
    async def segment_insert(self, segments: Iterable[mdl.Segment]) -> None:
        """Create new segments.

        :param segments: New segment objects to create.
        :raises UniqueError: One or several names already exist.
        """
        try:
            async with self.pg.transaction():
                await self.pg.executemany(
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
        except pg.UniqueError as exc:
            raise error.UniqueError from exc

    @backoff(
        *pg.PG_CONNECTION_ERRORS,
        max_retries=3,
    )
    async def segment_select(
        self, *, limit: int, offset: int, name: str, user_id: int | None
    ) -> mdl.List[mdl.Segment]:
        """List existing segments.

        Comes with pagination and optional filtering.
        :param limit: How many segments to return.
        :param offset: How many segments to skip.
        :param name: Set to search for a segment with specific name.
        :param user_id: ID of the user whose segments to return.
        :return: List of segments found.
        """
        if name and user_id is not None:
            db_result = await self.pg.fetch(
                """SELECT *
                FROM segments
                INNER JOIN segment_user ON segment_user.seg = segments.id
                WHERE segment_user.usr = $1 AND segments.name = $2
                ORDER BY id LIMIT $3 OFFSET $4
                """,
                user_id,
                name,
                limit,
                offset,
            )
        elif user_id:
            db_result = await self.pg.fetch(
                """SELECT *
                FROM segments
                INNER JOIN segment_user ON segment_user.seg = segments.id
                WHERE segment_user.usr = $1
                ORDER BY id LIMIT $2 OFFSET $3
                """,
                user_id,
                limit,
                offset,
            )
        elif name:
            db_result = await self.pg.fetch(
                """SELECT *
                FROM segments
                WHERE name = $1
                ORDER BY id LIMIT $2 OFFSET $3""",
                name,
                limit,
                offset,
            )
        else:
            db_result = await self.pg.fetch(
                """SELECT *
                FROM segments
                ORDER BY id LIMIT $1 OFFSET $2""",
                limit,
                offset,
            )

        # Intentionally leave this as **, to make sure models are updated
        #  when database updates - pydantic will point which fields
        #  aren't updated in the model
        return mdl.List[mdl.Segment](
            it=tuple(mdl.Segment(**row) for row in db_result)
        )

    @backoff(
        *pg.PG_CONNECTION_ERRORS,
        max_retries=3,
    )
    async def segment_update(self, ids_names: Mapping[UUID, str]) -> None:
        """Update segments names by their IDs.

        :param ids_names: Mapping of IDs to new names.
        :raises UniqueError: One of the names already exists in the database.
        """
        try:
            async with self.pg.transaction():
                await self.pg.executemany(
                    """UPDATE segments
                    SET name     = $2,
                        modified = (now() at time zone 'UTC')
                    WHERE id = $1""",
                    ids_names.items(),
                )
        except pg.UniqueError as exc:
            raise error.UniqueError from exc

    @backoff(
        *pg.PG_CONNECTION_ERRORS,
        max_retries=3,
    )
    async def segment_delete(
        self,
        *,
        segments_names: Sequence[str],
        segments_ids: Sequence[UUID],
    ) -> None:
        """Delete segments by their names or IDs.

        :param segments_names: Names of segments to delete.
        :param segments_ids: IDs of segments to delete.
        """
        if segments_names and segments_ids:
            await self.pg.execute(
                """DELETE
                FROM segments
                WHERE name = any ($1::text[])
                   OR id = any ($2::uuid[])""",
                segments_names,
                segments_ids,
            )
        elif segments_names:
            await self.pg.execute(
                """DELETE
                FROM segments
                WHERE name = any ($1::text[])""",
                segments_names,
            )
        elif segments_ids:
            await self.pg.execute(
                """DELETE
                FROM segments
                WHERE id = any ($1::uuid[])""",
                segments_ids,
            )

    @backoff(
        *pg.PG_CONNECTION_ERRORS,
        max_retries=3,
    )
    async def user_upsert(self, ids: Iterable[int]) -> None:
        """Insert user IDs, ignore duplicate IDs.

        :param ids: User IDs to insert.
        """
        await self.pg.executemany(
            """INSERT INTO users (id)
            VALUES ($1)
            ON CONFLICT (id) DO NOTHING""",
            ((user_id,) for user_id in ids),
        )

    @backoff(
        *pg.PG_CONNECTION_ERRORS,
        max_retries=3,
    )
    async def user_select(
        self, *, limit: int, offset: int, segment_id: UUID | None
    ) -> mdl.List[mdl.User]:
        """List existing user IDs.

        :param limit: How many IDs to return.
        :param offset: How many IDs to skip.
        :param segment_id: ID of segment to find users of.
        :return: List of IDs.
        """
        if segment_id:
            db_result = await self.pg.fetch(
                """SELECT *
                FROM users
                INNER JOIN segment_user ON users.id = segment_user.usr
                WHERE segment_user.seg = $1
                ORDER BY id LIMIT $2 OFFSET $3
                """,
                segment_id,
                limit,
                offset,
            )
        else:
            db_result = await self.pg.fetch(
                """SELECT *
                FROM users
                ORDER BY id LIMIT $1 OFFSET $2""",
                limit,
                offset,
            )
        return mdl.List[mdl.User](
            it=tuple(mdl.User(**row) for row in db_result)
        )

    @backoff(
        *pg.PG_CONNECTION_ERRORS,
        max_retries=3,
    )
    async def user_update(self, ids_newids: Mapping[int, int]) -> None:
        """Change user IDs.

        Change given user IDs into new ones.
        :param ids_newids: Mapping of old IDs to new IDs.
        :raises UniqueError: One of the new IDs already exists.
        """
        try:
            async with self.pg.transaction():
                await self.pg.executemany(
                    """UPDATE users
                    SET id = $2
                    WHERE id = $1""",
                    ids_newids.items(),
                )
        except pg.UniqueError as exc:
            raise error.UniqueError from exc

    @backoff(
        *pg.PG_CONNECTION_ERRORS,
        max_retries=3,
    )
    async def user_delete(self, user_ids: Sequence[int]) -> None:
        """Delete given IDs.

        :param user_ids: IDs to delete.
        """
        await self.pg.execute(
            """DELETE FROM users
            WHERE id = any($1::int[])""",
            user_ids,
        )

    async def user_iter(
        self, subset_segment_id: UUID | None
    ) -> AsyncIterator[mdl.User]:
        """Iterate users.

        If ``subset_segment_id`` isn't None, yields users from it;
        otherwise from entire database.
        :return: Users iterator.
        """
        if subset_segment_id is None:
            cursor_factory = self.pg.cursor('SELECT * FROM users')
        else:
            cursor_factory = self.pg.cursor(
                """SELECT *
                FROM users
                INNER JOIN segment_user
                    ON users.id = segment_user.usr
                    WHERE segment_user.seg = $1""",
                subset_segment_id,
            )

        async with self.pg.transaction():
            async for row in cursor_factory:
                yield mdl.User(**row)

    @backoff(
        *pg.PG_CONNECTION_ERRORS,
        max_retries=3,
    )
    async def segusr_insert(self, sus: Iterable[mdl.SegUsr]) -> None:
        """Create new segment-user relations.

        Existing relations are ignored.
        :param sus: New segment-user objects to create.
        """
        await self.pg.executemany(
            """INSERT INTO segment_user (seg, usr)
                VALUES ($1, $2)
                ON CONFLICT (seg, usr) DO NOTHING""",
            ((su.seg, su.usr) for su in sus),
        )

    @backoff(
        *pg.PG_CONNECTION_ERRORS,
        max_retries=3,
    )
    async def segusr_select(
        self,
        *,
        user_ids: Sequence[int],
        segment_ids: Sequence[UUID],
        limit: int,
        offset: int,
    ) -> mdl.List[mdl.SegUsr]:
        """List existing segment-user relations.

        Comes with pagination and optional filtering.
        Results are not cached.
        :param user_ids: IDs of users to include. Empty for no filtering.
        :param segment_ids: IDs of segments to include. Empty for no filtering.
        :param limit: How many segments to return.
        :param offset: How many segments to skip.

        :return: List of relations found.
        """
        if user_ids and segment_ids:
            db_result = await self.pg.fetch(
                """SELECT *
                FROM segment_user
                WHERE
                    usr = any($1::int[]) AND
                    seg = any($2::uuid[])
                ORDER BY usr
                LIMIT $3 OFFSET $4""",
                user_ids,
                segment_ids,
                limit,
                offset,
            )
        elif user_ids:
            db_result = await self.pg.fetch(
                """SELECT *
                    FROM segment_user
                    WHERE usr = any ($1::int[])
                    ORDER BY usr
                    LIMIT $2 OFFSET $3""",
                user_ids,
                limit,
                offset,
            )
        elif segment_ids:
            db_result = await self.pg.fetch(
                """SELECT *
                    FROM segment_user
                    WHERE seg = any ($1::uuid[])
                    ORDER BY usr
                    LIMIT $2 OFFSET $3""",
                segment_ids,
                limit,
                offset,
            )
        else:
            db_result = await self.pg.fetch(
                """SELECT *
                    FROM segment_user
                    ORDER BY usr
                    LIMIT $1 OFFSET $2""",
                limit,
                offset,
            )

        return mdl.List[mdl.SegUsr](
            it=tuple(mdl.SegUsr(**row) for row in db_result)
        )

    @backoff(
        *pg.PG_CONNECTION_ERRORS,
        max_retries=3,
    )
    async def segusr_delete(
        self,
        *,
        user_ids: Sequence[int],
        segment_ids: Sequence[UUID],
    ) -> None:
        """Delete segment-user relations by IDs of users or segments.

        :param user_ids: IDs of users to delete.
        :param segment_ids: IDs of segments to delete.
        """
        if user_ids and segment_ids:
            await self.pg.execute(
                """DELETE
                    FROM segment_user
                    WHERE
                        usr = any($1::int[]) AND
                        seg = any($2::uuid[])""",
                user_ids,
                segment_ids,
            )
        elif user_ids:
            await self.pg.execute(
                """DELETE
                    FROM segment_user
                    WHERE usr = any($1::int[])""",
                user_ids,
            )
        elif segment_ids:
            await self.pg.execute(
                """DELETE
                    FROM segment_user
                    WHERE seg = any($1::uuid[])""",
                segment_ids,
            )


def get_service(
    db: Annotated[pg.PostgresConnection, Depends(pg.get_pg)],
) -> DbService:
    """Service factory as a FastAPI dependency.

    :param db: Database connection.
    :returns: ``DbService`` instance.
    """
    return DbService(db)
