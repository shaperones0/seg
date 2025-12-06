"""Segment creation/assignation related endpoints."""

from typing import Annotated
from uuid import UUID
import textwrap as tw

from fastapi import APIRouter, Depends, status, Body, Query
from pydantic import AfterValidator

from seg.core import error, format
from seg.service import segment as service_segment
from seg.api.v1 import schema
from seg.core.config import PATTERN_SEG_NAME

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
        name: Annotated[
            str | None,
            Query(
                title="Name to search for",
                description=tw.dedent(
                    """Name of the segment to look for 
                    in the database; omit for no filtering"""),
                max_length=255,
                min_length=1,
                regex=PATTERN_SEG_NAME
            )
        ] = None
) -> list[schema.SegmentView]:
    """List all available segments."""

    segments = await segment.segments_view(
        limit=pgl,
        offset=pgi * pgl,
        name=name
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
            Body(
                title="Names of segments to create",
                description="Names of segments to create",
                min_length=1,
                max_length=100,
                regex=PATTERN_SEG_NAME
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
            Body(
                title="Names of segments to delete (optional)",
                description="Names of segments to delete",
                min_length=1,
                max_length=1000,
                regex=PATTERN_SEG_NAME
            )
        ] = None,
        ids: Annotated[
            list[UUID] | None,
            Body(
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


@router.put(
    '/',
    summary='Update segments',
    responses=format.responses(
        errors={

        },
        descriptions={

        }
    )
)
async def update(
        segment: Annotated[
            service_segment.SegmentService,
            Depends(service_segment.get_service)
        ],
        updates: Annotated[
            list[schema.InputSegmentUpdate],
            Body(
                title="Names of segments to update",
                description="Names of segments to update",
            )
        ]
) -> None:
    """Update segments."""

    await segment.segments_update(
        ids_names={upd.id: upd.new_name for upd in updates}
    )
