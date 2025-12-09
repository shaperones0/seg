"""Segment assignation API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status

from seg.api.v1.schema import SegmentUserView
from seg.core import error
from seg.core import format as fmt
from seg.service import segment_user as service_segment_user

router = APIRouter()


@router.get(
    '/',
    summary='List user-segment relations with filters',
    responses=fmt.responses(
        errors={},
        descriptions={
            status.HTTP_503_SERVICE_UNAVAILABLE: error.MSG_503,
        },
    ),
)
async def view(
    segment_user: Annotated[
        service_segment_user.SegmentUserService,
        Depends(service_segment_user.get_service),
    ],
    user_ids: Annotated[
        list[int],
        Body(
            default_factory=list,
            title='Ids of users to include',
            description='List of user ids; omit for no filtering',
            min_items=0,
            max_items=1000,
        ),
    ],
    segment_ids: Annotated[
        list[UUID],
        Body(
            default_factory=list,
            title='Ids of segments to include',
            description='List of segment ids; omit for no filtering',
            min_items=0,
            max_items=1000,
        ),
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
) -> list[SegmentUserView]:
    """## List stored segment-user relations.

    Supports optional filtering by user IDs or segment ID.

    Results not cached in most cases, unless specified otherwise.

    Specify only one segment ID and no user IDs to fetch all users
    in this segment. This variant of the query is cached.

    Specify only one user ID and no segment IDs to fetch all segments
    this user is in. This variant of the query is cached.

    ### Parameters:
    - `user_ids`: IDs of users to include, leave empty to include all users;
    - `segment_ids`: IDs of segments to include,
      leave empty to include all segments;
    - `pgi`: Page index (from 0 to 10 000);
    - `pgl`: Page length (from 0 to 1000);
    """
    sus = await segment_user.su_view(
        user_ids=user_ids,
        segment_ids=segment_ids,
        offset=pgi * pgl,
        limit=pgl,
    )
    return [
        SegmentUserView(user_id=su.user, segment_id=su.segment)
        for su in sus.items
    ]
