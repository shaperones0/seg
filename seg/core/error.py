"""Internal errors used by API services.

Most errors use code 400.

Code 429 is reserved for ``TooManyRequestsError``.
Code 503 is reserved for ``ServiceUnavailable``.
"""

from typing import ClassVar, Self

from fastapi import status
from pydantic import BaseModel


class RequestError(Exception):
    status_code: ClassVar[int] = status.HTTP_400_BAD_REQUEST


class BackoffError(ConnectionError, RequestError):
    status_code: ClassVar[int] = status.HTTP_503_SERVICE_UNAVAILABLE

    def __init__(self, func_name: str, retries: int) -> None:
        super(ConnectionError, self).__init__(
            f"{func_name} didn't respond after {retries} retries"
        )


class ErrInfo(BaseModel):
    """Error info model."""

    err_cls: str
    err_msg: str

    @classmethod
    def from_err(cls, err: BaseException) -> Self:
        return cls(
            err_cls=err.__class__.__name__,
            err_msg=str(err),
        )

    @classmethod
    def from_err_cls(
            cls,
            err_cls: type[BaseException],
            msg: str | None = None
    ) -> Self:
        return cls(
            err_cls=err_cls.__name__,
            err_msg=msg if msg is not None else err_cls.__name__
        )
