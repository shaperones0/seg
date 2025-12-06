"""API schema"""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from seg.core.config import PATTERN_SEG_NAME


class SegmentView(BaseModel):
    id: UUID
    name: str


class InputSegmentName(BaseModel):
    name: Annotated[
        str,
        Field(
            pattern=PATTERN_SEG_NAME,
            min_length=1,
            max_length=100,
        )
    ]


class InputSegmentUpdate(BaseModel):
    id: UUID
    new_name: str


class UserView(BaseModel):
    id: int


class InputUserUpdate(BaseModel):
    id: int
    new_id: int
