"""Discover and apply migrations."""

import os
import sys
from collections.abc import Callable
from logging import getLogger
from pathlib import Path
from types import ModuleType
from typing import Self

from psqlpy import Connection

from migrations.base import BaseMigration

logger = getLogger(__name__)


def _dispatch(
        idx: int | str | None,
        *,
        none_value: int,
        str_lambda: Callable[[str], int]) -> int:
    if idx is None:
        return none_value
    if isinstance(idx, str):
        return str_lambda(idx)
    if isinstance(idx, int):
        return idx
    raise TypeError(f"Expected str, int or None but got {type(idx)}")


def import_from_path(module_name: str, file_path: Path) -> ModuleType:
    """Import a module from a path.

    :param module_name: Name to give imported module.
    :param file_path: Path to the module.
    :return: Imported module instance.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class MigrationDict:
    """Migration collection."""

    def __init__(self, migrations: dict[str, BaseMigration]) -> None:
        """Initialize the migration collection.

        :param migrations: Dictionary of migration instances.
        """
        self.migrations = migrations

    @classmethod
    def from_path(
            cls,
            connection: Connection,
            base_dir: str | os.PathLike[str] | None = None
    ) -> Self:
        """Generate migration dictionary from python files in given directory.

        :param connection: Database connection.
        :param base_dir: Directory to look for migration in.
        :return: Migration dictionary.
        """
        if base_dir is None:
            base_path = Path(__file__).parent.resolve() / "migrations"
        else:
            base_path = Path(base_dir)

        migrations: dict[str, BaseMigration] = {}
        for file in base_path.iterdir():
            if file.name in ["__init__.py", "__pycache__"]:
                continue

            if not file.is_file() or file.suffix != ".py":
                logger.warning(
                    "Encountered bad entry in migrations search path: %s",
                    file
                )
                continue

            module = import_from_path(file.stem, file)
            if not hasattr(module, "Migration"):
                logger.warning(
                    "Failed to find migration object in migration file: %s",
                    file
                )
                continue

            migration_cls: type[BaseMigration] = module.Migration
            migrations[file.stem] = migration_cls(connection)

        return cls(migrations)

    async def upgrade(self, applied_migrations: list[str]) -> list[str]:
        """Upgrade the database up to the latest migration.

        :param applied_migrations: Migrations assumed to be applied.
        :return: List of applied migrations.
        """
        done_migrations: list[str] = []
        for migration_name, migration in self.migrations.items():
            if migration_name in applied_migrations:
                logger.info("migration %s: SKIP", migration_name)
                continue
            logger.info("migration %s: PENDING", migration_name)
            await migration.upgrade()
            done_migrations.append(migration_name)
        return done_migrations


class MigrationManager:
    """Manage lists of applied migrations."""

    def __init__(self, connection: Connection) -> None:
        """Create a new migration manager.

        :param connection: Postgres connection.
        """
        self.connection = connection

    async def prepare_table_if_need(self) -> None:
        """Generate migration table if necessary."""
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                name VARCHAR(255) PRIMARY KEY NOT NULL,
                applied_at TIMESTAMP with time zone NOT NULL
                    DEFAULT (now() at time zone 'utc')
            )
        """)

    async def read_applied_migrations(self) -> list[str]:
        """Return list of applied migrations in the database.

        :return: List of applied migration names.
        """
        rows = await self.connection.fetch("""
            SELECT name, applied_at FROM migrations
        """)

        applied: list[str] = []
        for row in rows.result():
            logger.debug("applied: %s at %s", row["name"], row["applied_at"])
            applied.append(row["name"])
        return applied

    async def write_applied_migration(self, migration_names: list[str]) -> None:
        """Write applied migrations in the database.

        :param migration_names: Names of applied migrations.
        """
        await self.connection.execute_many(
            """INSERT INTO migrations (name)
               VALUES ($1)
               ON CONFLICT DO NOTHING""",
            [[name] for name in migration_names]
        )
