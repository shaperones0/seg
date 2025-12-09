"""Segment internal model."""

from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel


class List[T_item: BaseModel](BaseModel):
    """Abstract immutable collection.

    Used primarily for easier storage in Redis.
    """

    it: tuple[T_item, ...]


class Segment(BaseModel):
    """Segment model."""

    id: UUID
    name: str

    created: datetime
    modified: datetime

    @classmethod
    def create(cls, name: str) -> Self:
        """Create a new segment.

        Gives the segment random UUID, and current timestamps.
        :param name: The name of the segment.
        :returns: The created segment.
        """
        return cls(
            id=uuid4(),
            name=name,
            created=datetime.now(UTC),
            modified=datetime.now(UTC),
        )


class User(BaseModel):
    """User model."""

    id: int


class SegUsr(BaseModel):
    """Segment-to-user relation."""

    seg: UUID
    usr: int
