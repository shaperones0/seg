"""Segment model."""

from typing import Self
from uuid import UUID, uuid4
from datetime import datetime, UTC

from pydantic import BaseModel


class Segment(BaseModel):
    """Segment model."""

    id: UUID
    name: str

    created: datetime
    modified: datetime

    @classmethod
    def create(cls, name: str) -> Self:
        """Create a new segment.

        :param name: The name of the segment.
        :returns: The created segment.
        """

        return cls(
            id=uuid4(),
            name=name,
            created=datetime.now(UTC),
            modified=datetime.now(UTC)
        )


class SegmentList(BaseModel):
    items: list[Segment]


class SegmentUser(BaseModel):
    """Segment-to-user relation."""

    segment: UUID
    user: int


class SegmentUsers(BaseModel):
    items: list[SegmentUser]