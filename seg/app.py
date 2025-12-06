"""API Service entrypoint.

Sets up FastAPI app, together with database connection
based on environment variables settings.
"""

from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from logging import getLogger
from typing import NoReturn
from urllib.parse import urlparse
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import ORJSONResponse
from starlette.datastructures import MutableHeaders

from seg.api.v1 import (
    segment as api_segment,
    user as api_user,
)
from seg.core.config import SETTINGS
from seg.db import pg, redis
from seg.core.error import RequestError, ErrInfo

logger = getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    """FastAPI lifespan context manager.

    Sets up connections to databases and closes them when the
    app exits, regardless of status.
    """
    await pg.init(SETTINGS.pg.url)
    await redis.init(SETTINGS.redis.url)

    yield

    await pg.close()
    await redis.close()


app = FastAPI(
    # Project name shows up in documentation
    title=SETTINGS.project_name,

    # Replace standard JSON serializer with
    #  faster serializer ORJSON written in Rust
    default_response_class=ORJSONResponse,

    # Setup lifespan for connections
    lifespan=lifespan
)


@app.exception_handler(RequestError)
def request_error_handler(_: Request, exc: RequestError) -> NoReturn:
    raise HTTPException(
        status_code=exc.status_code,
        detail=ErrInfo.from_err(exc).model_dump()
    )


app.include_router(api_segment.router, prefix="/api/v1/seg", tags=["segment"])
app.include_router(api_user.router, prefix="/api/v1/u", tags=["user"])


def main() -> None:
    """Application entrypoint."""
    import uvicorn
    parsed = urlparse(SETTINGS.api_url)
    if parsed.hostname is None or parsed.port is None:
        raise ValueError("Invalid API url")

    uvicorn.run(app, host=parsed.hostname, port=parsed.port)


if __name__ == "__main__":
    main()
