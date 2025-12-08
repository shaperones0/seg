"""Internal errors used by API services.

Most errors use code 400.

Code 429 is reserved for ``TooManyRequestsError``.
Code 503 is reserved for ``ServiceUnavailable``.
"""

from collections.abc import Sequence
from typing import ClassVar, Self

from fastapi import status
from pydantic import BaseModel

ErrType = type[BaseException]
ErrListType = Sequence[ErrType]


class RequestError(Exception):
    """Base exception for my custom errors.

    Contains ``status_code`` for use in FastAPI exception handler.
    """

    status_code: ClassVar[int] = status.HTTP_400_BAD_REQUEST


ReqErrType = type[RequestError]
ReqErrListType = Sequence[ReqErrType]


class BackoffError(ConnectionError, RequestError):
    """Service failed to respond after maximum number of retries."""

    status_code: ClassVar[int] = status.HTTP_503_SERVICE_UNAVAILABLE

    def __init__(self, service_name: str) -> None:
        """Standard exception initializer.

        Takes the name of the service for incident reporting.
        :param service_name: Name of the service from where the exception
          was raised.
        """
        ConnectionError.__init__(
            self, f"{service_name} can't establish internal connection."
        )


class UniqueError(RequestError):
    """Unique constraint violation."""


class ErrInfo(BaseModel):
    """Error info model."""

    err_cls: str
    err_msg: str

    @classmethod
    def from_err(cls, err: BaseException) -> Self:
        """Generate error info model from any exception instance.

        Copies error message from the instance.
        :param err: Exception to generate info from.
        :return: Generated error info model.
        """
        return cls(
            err_cls=err.__class__.__name__,
            err_msg=str(err),
        )

    @classmethod
    def from_err_cls(cls, err_cls: ErrType, msg: str | None = None) -> Self:
        """Generate error info model from exception class and custom message.

        :param err_cls: Exception class to generate info from.
        :param msg: Error message.
        :return: Generated error info model.
        """
        return cls(
            err_cls=err_cls.__name__,
            err_msg=msg or err_cls.__name__,
        )
