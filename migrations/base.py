"""Base migrations class."""

from abc import ABC, abstractmethod

from psqlpy import Connection


class BaseMigration(ABC):
    """Base migration class.

    Inherit it to create your own migrations.
    """

    def __init__(self, conn: Connection) -> None:
        """Initialize the migrations with given database connection.

        :param conn: Database connection.
        """
        self.conn = conn

    @abstractmethod
    async def upgrade(self) -> None:
        """Apply the migration."""
        raise NotImplementedError

    async def downgrade(self) -> None:
        """Revert the migration."""
        raise NotImplementedError
