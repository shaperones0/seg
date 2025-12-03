"""Initial migration.

Creates the tables:
- users
- login_history
- revoked_*

Also set up indexes where needed.
"""

from logging import getLogger

from migrations.base import BaseMigration

logger = getLogger(__name__)


class Migration(BaseMigration):
    """Initial migration."""

    async def upgrade(self) -> None:
        """Do the initial migration.

        Create the tables:
        - users
        - login_history
        - revoked_*

        Also set up indexes where needed.
        """
        logger.info("Creating segments, segment_user tables")
        await self.conn.execute("""
        CREATE TABLE segments (
            id UUID PRIMARY KEY NOT NULL,
            name VARCHAR(255) UNIQUE NOT NULL,
            
            created TIMESTAMP with time zone NOT NULL
                DEFAULT (now() at time zone 'UTC'),
            modified TIMESTAMP with time zone NOT NULL
                DEFAULT (now() at time zone 'UTC')
        )""")
        await self.conn.execute("""
        CREATE TABLE segment_user (
            segment UUID NOT NULL REFERENCES segments (id)
                ON DELETE CASCADE,
            user_id INT NOT NULL 
        )""")
        await self.conn.execute("""
        CREATE INDEX segment_user_id ON segment_user (user_id)
        """)

    async def downgrade(self) -> None:
        """Rollback the initial migration.

        Deletes created tables and indices.
        """
        logger.info("Deleting users, revoked_* and login_history tables")
        await self.conn.execute("DROP TABLE segment_user")
        await self.conn.execute("DROP TABLE segments")
        await self.conn.execute("DROP INDEX segment_user_id")
