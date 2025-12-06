"""API schema"""

from uuid import UUID

from pydantic import BaseModel


class SegmentView(BaseModel):
    id: UUID
    name: str


class InputSegmentUpdate(BaseModel):
    id: UUID
    new_name: str
