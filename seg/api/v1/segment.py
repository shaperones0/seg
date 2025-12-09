"""Segment CRUD API."""

import textwrap as tw
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status

from seg.api.v1 import schema
from seg.core import error
from seg.core import format as fmt
from seg.core.config import PATTERN_SEG_NAME
from seg.service import segment as service_segment

router = APIRouter()


@router.get(
    '/',
    summary='List all available segments',
    responses=fmt.responses(
        errors={},
        descriptions={
            status.HTTP_503_SERVICE_UNAVAILABLE: error.MSG_503,
        },
    ),
)
async def view(
    segment: Annotated[
        service_segment.SegmentService, Depends(service_segment.get_service)
    ],
    pgi: Annotated[
        int,
        Query(
            title='Page number',
            description='Page number [0 - 10 000)',
            lt=10_000,
            ge=0,
        ),
    ] = 0,
    pgl: Annotated[
        int,
        Query(
            title='Number of elements per page',
            description='Number of elements on page [1 - 1000]',
            le=1000,
            ge=1,
        ),
    ] = 10,
    name: Annotated[
        str | None,
        Query(
            title='Name to search for',
            description=tw.dedent(
                """Name of the segment to look for
                    in the database; omit for no filtering"""
            ),
            max_length=255,
            min_length=1,
            regex=PATTERN_SEG_NAME,
        ),
    ] = None,
) -> list[schema.SegmentView]:
    """## List stored segments.

    Retrieve a list of segments stored in the database.
    Supports pagination using params `pgi` (page index) and `pgl` (page length).
    Optionally, add `name` to search for specific name in the database.

    The results are cached.

    ### Parameters:
    - `pgi`: Page index (from 0 to 10 000);
    - `pgl`: Page length (from 0 to 1000);
    - `name`: Segment name to search for.

    ### Returns:
    List of segments.
    """
    segments = await segment.segments_view(
        limit=pgl, offset=pgi * pgl, name=name or ''
    )

    return [
        schema.SegmentView(id=seg.id, name=seg.name) for seg in segments.items
    ]


@router.post(
    '/',
    summary='Create a new segment',
    responses=fmt.responses(
        errors={error.UniqueError: 'One or more names are already occupied.'},
        descriptions={
            status.HTTP_503_SERVICE_UNAVAILABLE: error.MSG_503,
            status.HTTP_400_BAD_REQUEST: 'Generic bad request',
        },
    ),
)
async def create(
    segment: Annotated[
        service_segment.SegmentService, Depends(service_segment.get_service)
    ],
    names: Annotated[
        list[schema.InputSegmentName],
        Body(
            title='Names of segments to create',
            description='Names of segments to create',
            min_length=1,
            max_length=100,
        ),
    ],
) -> list[schema.SegmentView]:
    """## Create new segments.

    Create new segments from names list.

    ### Parameters:
    - `names`: Names of segments to create.

    ### Returns:
    List of new segments.
    """
    segments = await segment.segment_create(nm.name for nm in names)
    return [schema.SegmentView(id=seg.id, name=seg.name) for seg in segments]


@router.delete(
    '/',
    summary='Delete segments',
    responses=fmt.responses(
        errors={},
        descriptions={
            status.HTTP_503_SERVICE_UNAVAILABLE: error.MSG_503,
        },
    ),
)
async def delete(
    segment: Annotated[
        service_segment.SegmentService, Depends(service_segment.get_service)
    ],
    names: Annotated[
        list[schema.InputSegmentName],
        Body(
            default_factory=list,
            title='Names of segments to delete (optional)',
            description='Names of segments to delete',
            min_length=1,
            max_length=1000,
        ),
    ],
    ids: Annotated[
        list[UUID],
        Body(
            default_factory=list,
            title='IDs of segments to delete (optional)',
            description='IDs of segments to delete',
            max_length=1000,
        ),
    ],
) -> None:
    """Delete segments."""
    await segment.segments_delete(
        segments_names=[seg.name for seg in names],
        segments_ids=ids,
    )


@router.put(
    '/',
    summary='Update segments',
    responses=fmt.responses(
        errors={error.UniqueError: 'One or more names are already occupied.'},
        descriptions={
            status.HTTP_503_SERVICE_UNAVAILABLE: error.MSG_503,
            status.HTTP_400_BAD_REQUEST: 'Generic bad request',
        },
    ),
)
async def update(
    segment: Annotated[
        service_segment.SegmentService, Depends(service_segment.get_service)
    ],
    updates: Annotated[
        list[schema.InputSegmentUpdate],
        Body(
            title='Names of segments to update',
            description='Names of segments to update',
        ),
    ],
) -> None:
    """Update segments."""
    await segment.segments_update(
        ids_names={upd.id: upd.new_name for upd in updates}
    )
