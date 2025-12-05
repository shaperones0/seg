"""Contains BaseSettings model for loading environment settings.

Default values assume local development environment:
- Redis is open on port 6380,
- Postgres is open on port 5433.
"""


from logging import config as logging_config
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

from seg.core.log import LOGGING


class RedisSettings(BaseSettings):
    """Redis database connection settings."""

    model_config = SettingsConfigDict(env_prefix="redis_")
    url: str = "redis://localhost:6379"


class PostgresSettings(BaseSettings):
    """Postgres database connection settings."""

    model_config = SettingsConfigDict(env_prefix="postgres_")
    url: str = "postgres://postgres:postgres@localhost:5432/seg?target_session_attrs=read-write"


class Settings(BaseSettings):
    """Project settings."""

    project_name: str = "segmentation"
    debug: bool = True

    api_url: str = "http://localhost:8000"

    redis: RedisSettings = RedisSettings()
    pg: PostgresSettings = PostgresSettings()


logging_config.dictConfig(LOGGING)


if find_dotenv():
    load_dotenv()


SETTINGS = Settings()
BASE_DIR = Path(__file__).resolve().parent.parent
