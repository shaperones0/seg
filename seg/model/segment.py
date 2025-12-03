"""Segment model."""

from uuid import UUID
from datetime import datetime

from pydantic import BaseModel


class Segment(BaseModel):
    """Segment model."""

    id: UUID
    name: str

    created: datetime
    modified: datetime


class SegmentUser(BaseModel):
    """Segment-to-user relation."""

    segment: UUID
    user: int
