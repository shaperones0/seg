"""Segmentation service API v1 schema."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from seg.core.config import PATTERN_SEG_NAME


class SegmentView(BaseModel):
    """Lite version of segment object."""

    id: UUID
    name: str


class InputSegmentName(BaseModel):
    """Segment name type with proper restrictions.

    Limits the length to from 1 to 100 characters,
    and checks for a regex pattern in the name.
    """

    name: Annotated[
        str,
        Field(
            pattern=PATTERN_SEG_NAME,
            min_length=1,
            max_length=100,
        ),
    ]


class InputSegmentUpdate(BaseModel):
    """Key-value pair to update a segment name by its id."""

    id: UUID
    new_name: str


class UserView(BaseModel):
    """Lite version of user object."""

    id: int


class InputUserUpdate(BaseModel):
    """Key-value pair to give a user new id."""

    id: int
    new_id: int
