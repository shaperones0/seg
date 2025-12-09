"""Segment assignation API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status

from seg.api.v1 import schema
from seg.core import error
from seg.core import format as fmt
from seg.model import model as mdl
from seg.service import segment_user as svc_segusr

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
        svc_segusr.SegmentUserService,
        Depends(svc_segusr.get_service),
    ],
    user_ids: Annotated[
        list[int],
        Query(
            default_factory=list,
            title='IDs of users to include',
            description='List of user IDs; omit for no filtering',
            min_items=0,
            max_items=1000,
        ),
    ],
    segment_ids: Annotated[
        list[UUID],
        Query(
            default_factory=list,
            title='IDs of segments to include',
            description='List of segment IDs; omit for no filtering',
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
) -> list[schema.SegmentUser]:
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
    - `pgl`: Page length (from 0 to 1000).
    """
    sus = await segment_user.segusr_read(
        user_ids=user_ids,
        segment_ids=segment_ids,
        offset=pgi * pgl,
        limit=pgl,
    )
    return [schema.SegmentUser(user_id=su.usr, segment_id=su.seg) for su in sus]


@router.post(
    '/',
    summary='Create new user-segment relations',
    responses=fmt.responses(
        errors={},
        descriptions={
            status.HTTP_503_SERVICE_UNAVAILABLE: error.MSG_503,
        },
    ),
)
async def create(
    segment_user: Annotated[
        svc_segusr.SegmentUserService,
        Depends(svc_segusr.get_service),
    ],
    su: Annotated[
        list[schema.SegmentUser],
        Body(
            default_factory=list,
            title='Relations to create',
            description='User-segment relations; omit for no filtering',
            min_items=1,
            max_items=1000,
        ),
    ],
) -> None:
    """## Create new user-segment relations.

    Duplicate relations are ignored.

    ### Parameters:
    - `user_ids`: Pairs of user IDs and segment IDs to include.
    """
    await segment_user.segusr_create(
        [
            mdl.SegUsr(seg=seg_user.segment_id, usr=seg_user.user_id)
            for seg_user in su
        ]
    )


@router.delete(
    '/',
    summary='Delete user-segment relations',
    responses=fmt.responses(
        errors={},
        descriptions={
            status.HTTP_503_SERVICE_UNAVAILABLE: error.MSG_503,
        },
    ),
)
async def delete(
    segment_user: Annotated[
        svc_segusr.SegmentUserService,
        Depends(svc_segusr.get_service),
    ],
    user_ids: Annotated[
        list[int],
        Body(
            default_factory=list,
            title='IDs of users to include',
            description='List of user IDs; omit for no filtering',
            min_items=0,
            max_items=1000,
        ),
    ],
    segment_ids: Annotated[
        list[UUID],
        Body(
            default_factory=list,
            title='IDs of segments to include',
            description='List of segment IDs; omit for no filtering',
            min_items=0,
            max_items=1000,
        ),
    ],
) -> None:
    """## Delete user-segment relations.

    Use user_ids and/or segment IDs to filter relations to delete.

    ### Parameters:
    - `user_ids`: Pairs of user IDs and segment IDs to include,
    - `segment_ids`: Pairs of segment IDs to include.
    """
    await segment_user.segusr_delete(
        user_ids=user_ids,
        segment_ids=segment_ids,
    )


@router.post(
    '/mass',
    summary='Assign segments to a percentage of users',
    responses=fmt.responses(
        errors={},
        descriptions={
            status.HTTP_503_SERVICE_UNAVAILABLE: error.MSG_503,
        },
    ),
)
async def mass(
    segment_user: Annotated[
        svc_segusr.SegmentUserService,
        Depends(svc_segusr.get_service),
    ],
    ratio: Annotated[
        float,
        Body(
            title='Users ratio',
            description='Ratio of users which get assigned to given segments',
            gt=0,
            le=1,
        ),
    ],
    segment_ids: Annotated[
        list[UUID],
        Body(
            default_factory=list,
            title='IDs of segments to assign',
            description='List of segment IDs',
            min_items=0,
            max_items=1000,
        ),
    ],
    subset_segment_id: Annotated[
        UUID | None,
        Body(
            title='Apply mass assign only to users in provided segment',
            description='Segment ID',
            min_items=0,
            max_items=1000,
        ),
    ] = None,
) -> None:
    """## Assign segments to a percentage of users.

    Param ``ratio`` sets the ratio of users assigned to given segments.
    Notice that, in case of several segments provided, the subset of users
    of each segment will be equal.

    In order to have random independent subsets
    use several consecutive calls with one segment each.

    Allows to only assign the segment to a fraction of all user base,
    or only members of a specific segment.

    ### Parameters:
    - `ratio`: Ratio of users to assign segment to.
    - `segment_ids`: Segment to assign.
    - `subset_segment_id`: Optional filter segment.
    """
    await segment_user.segusr_mass(
        ratio=ratio,
        segment_ids=segment_ids,
        subset_segment_id=subset_segment_id,
    )
