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
        logger.info("Creating segments, users and segment_user tables")

        await self.conn.execute("""
        CREATE TABLE segments
        (
            id       UUID PRIMARY KEY         NOT NULL,
            name     VARCHAR(255) UNIQUE      NOT NULL,

            created  TIMESTAMP with time zone NOT NULL
                DEFAULT (now() at time zone 'UTC'),
            modified TIMESTAMP with time zone NOT NULL
                DEFAULT (now() at time zone 'UTC')
        );
        CREATE TABLE users (
            id BIGSERIAL NOT NULL PRIMARY KEY
        );
        CREATE TABLE segment_user
        (
            seg UUID   NOT NULL REFERENCES segments (id)
                ON DELETE CASCADE,
            usr BIGINT NOT NULL REFERENCES users (id)
        );
        CREATE INDEX segment_user_seg ON segment_user (seg);
        CREATE INDEX segment_user_usr ON segment_user (usr);
        """)

    async def downgrade(self) -> None:
        """Rollback the initial migration.

        Deletes created tables and indices.
        """
        logger.info("Deleting users, revoked_* and login_history tables")
        await self.conn.execute("DROP TABLE segment_user")
        await self.conn.execute("DROP TABLE users")
        await self.conn.execute("DROP TABLE segments")
        await self.conn.execute("DROP INDEX segment_user_seg")
        await self.conn.execute("DROP INDEX segment_user_usr")
