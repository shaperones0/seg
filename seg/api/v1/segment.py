"""Segment creation/assignation related endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status, Form, Query
from pydantic import AfterValidator

from seg.core import error, format
from seg.service import segment as service_segment
from seg.api.v1 import schema

router = APIRouter()

@router.get(
    '/',
    summary='List all available segments',
    responses=format.responses(
        errors={

        },
        descriptions={

        }
    )
)
async def view(
        segment: Annotated[
            service_segment.SegmentService,
            Depends(service_segment.get_service)
        ],
        pgi: Annotated[
            int,
            Query(
                title="Page number",
                description="Page number [0 - 10_000)",
                lt=10_000,
                ge=0
            )
        ],
        pgl: Annotated[
            int,
            Query(
                title="Number of elements per page",
                description="Number of elements on page [1 - 1000]",
                le=1000,
                ge=1,
            )
        ],
        substr: Annotated[
            str | None,
            Query(
                title="Segment title substring",
                description="Substring to look for in segment titles",
                max_length=255,
                min_length=1
            )
        ] = None
) -> list[schema.SegmentView]:
    """List all available segments."""

    segments = await segment.segments_view(
        limit=pgl,
        offset=pgi * pgl,
        like=substr
    )

    return [
        schema.SegmentView(id=seg.id, name=seg.name)
        for seg in segments.items
    ]


@router.post(
    '/',
    summary='Create a new segment',
    responses=format.responses(
        errors={

        },
        descriptions={

        }
    )
)
async def create(
        segment: Annotated[
            service_segment.SegmentService,
            Depends(service_segment.get_service)
        ],
        names: Annotated[
            list[str],
            Query(
                title="Names of segments to create",
                description="Names of segments to create",
                min_length=1,
                max_length=100
            )
        ]
) -> None:
    """Create a new segment."""
    await segment.segment_create(names)


@router.delete(
    '/',
    summary='Delete segments',
    responses=format.responses(
        errors={

        },
        descriptions={

        }
    )
)
async def delete(
        segment: Annotated[
            service_segment.SegmentService,
            Depends(service_segment.get_service)
        ],
        names: Annotated[
            list[str] | None,
            Query(
                title="Names of segments to delete (optional)",
                description="Names of segments to delete",
                max_length=1000
            )
        ] = None,
        ids: Annotated[
            list[UUID] | None,
            Query(
                title="IDs of segments to delete (optional)",
                description="IDs of segments to delete",
                max_length=1000
            )
        ] = None,
) -> None:
    """Delete segments."""
    await segment.segments_delete(
        segments_names=names or [],
        segments_ids=ids or [],
    )
