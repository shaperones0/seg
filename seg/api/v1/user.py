"""Segment creation/assignation related endpoints."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from seg.api.v1 import schema
from seg.core import error
from seg.core import format as fmt
from seg.service import user as service_user

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
    user: Annotated[
        service_user.UserService, Depends(service_user.get_service)
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
) -> list[schema.UserView]:
    """List tracked users."""
    users = await user.user_view(
        limit=pgl,
        offset=pgi * pgl,
    )

    return [schema.UserView(id=usr.id) for usr in users.items]


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
    user: Annotated[
        service_user.UserService, Depends(service_user.get_service)
    ],
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
    """Create new users."""
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
    user: Annotated[
        service_user.UserService, Depends(service_user.get_service)
    ],
    ids: Annotated[
        list[int],
        Body(
            title='IDs of users to delete',
            description='IDs of users to delete',
            max_length=1000,
        ),
    ],
) -> None:
    """Delete users."""
    await user.user_delete(users_ids=ids)


@router.put(
    '/',
    summary='Update users',
    responses=fmt.responses(
        errors={
            error.UniqueError:
                'One or more IDs are already occupied.'
        },
        descriptions={
            status.HTTP_503_SERVICE_UNAVAILABLE: error.MSG_503,
            status.HTTP_400_BAD_REQUEST: 'Generic bad request',
        },
    ),
)  # fmt: skip
async def update(
    user: Annotated[
        service_user.UserService, Depends(service_user.get_service)
    ],
    updates: Annotated[
        list[schema.InputUserUpdate],
        Body(
            title='Ids of users to update',
            description='Ids of users to update',
        ),
    ],
) -> None:
    """Update users."""
    await user.user_update(ids_newids={upd.id: upd.new_id for upd in updates})
