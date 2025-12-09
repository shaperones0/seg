"""Segment creation/assignation related endpoints."""

import textwrap as tw
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status

from seg.api.v1 import schema
from seg.core import error
from seg.core import format as fmt
from seg.service import user as svc_user

router = APIRouter()


@router.get(
    '/',
    summary='List tracked users',
    responses=fmt.responses(
        errors={},
        descriptions={
            status.HTTP_503_SERVICE_UNAVAILABLE: error.MSG_503,
        },
    ),
)
async def view(
    user: Annotated[svc_user.UserService, Depends(svc_user.get_service)],
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
    segment_id: Annotated[
        UUID | None,
        Query(
            title='Segment ID to show users of',
            description='Segment ID',
        ),
    ] = None,
) -> list[schema.ViewUser]:
    """## List tracked users.

    Supports pagination.

    Results are cached.

    ### Parameters:
    - `pgi`: Page number;
    - `pgl`: Number of elements per page;
    - `segment_id`: Segment ID to show users of.

    ### Returns:
    List of users found.
    """
    users = await user.user_read(
        limit=pgl,
        offset=pgi * pgl,
        segment_id=segment_id,
    )

    return [schema.ViewUser(id=user_id) for user_id in users]


@router.post(
    '/',
    summary='Register new users',
    responses=fmt.responses(
        errors={},
        descriptions={
            status.HTTP_503_SERVICE_UNAVAILABLE: error.MSG_503,
        },
    ),
)
async def create(
    user: Annotated[svc_user.UserService, Depends(svc_user.get_service)],
    ids: Annotated[
        list[int],
        Body(
            title='Ids of users to register',
            description='Ids of users to register',
            min_length=1,
            max_length=100,
        ),
    ],
) -> None:
    """##Create new users.

    Resets the cache.

    ### Parameters:
    - `ids`: List of user IDs to register;
    """
    await user.user_add(ids)


@router.delete(
    '/',
    summary='Delete users',
    responses=fmt.responses(
        errors={},
        descriptions={
            status.HTTP_503_SERVICE_UNAVAILABLE: error.MSG_503,
        },
    ),
)
async def delete(
    user: Annotated[svc_user.UserService, Depends(svc_user.get_service)],
    ids: Annotated[
        list[int],
        Body(
            title='IDs of users to delete',
            description='IDs of users to delete',
            max_length=1000,
        ),
    ],
) -> None:
    """## Delete users.

    Resets the cache.

    ### Parameters:
    - `ids`: List of user IDs to delete;
    """
    await user.user_delete(ids)


@router.put(
    '/',
    summary='Update users',
    responses=fmt.responses(
        errors={
            error.UniqueError: tw.dedent(
                """One or more ids are already occupied,
                    or duplicate keys found."""
            )
        },
        descriptions={
            status.HTTP_503_SERVICE_UNAVAILABLE: error.MSG_503,
            status.HTTP_400_BAD_REQUEST: 'Generic bad request',
        },
    ),
)
async def update(
    user: Annotated[svc_user.UserService, Depends(svc_user.get_service)],
    updates: Annotated[
        list[schema.InputUserUpdate],
        Body(
            title='Ids of users to update',
            description='Ids of users to update',
        ),
    ],
) -> None:
    """## Update users.

    If any new ID already exists in the database, `UniqueError` is raised.

    Resets the cache.

    ### Parameters:
    - `updates`: List of key-value pairs to update;
    """
    if len({upd.id for upd in updates}) != len(updates):
        raise error.UniqueError

    await user.user_update({upd.id: upd.new_id for upd in updates})
