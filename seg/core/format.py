"""Swagger doc formatting helpers."""

from collections.abc import Mapping
from itertools import chain
from textwrap import dedent
from typing import Any

from seg.core import error


def responses(
    *,
    errors: dict[error.ReqErrType, str | None],
    descriptions: Mapping[int, str],
) -> dict[int | str, dict[str, Any]]:
    """Generate FastAPI responses param in APIRouter endpoints.

    :param errors: Possible errors.
    :param descriptions: Error descriptions and possible solutions.
    :return: Generated responses dict.
    """
    errors_sieved: dict[int, list[error.ReqErrType]] = {}
    for erm in errors:
        errors_sieved.setdefault(erm.status_code, []).append(erm)

    return {
        code: {
            'description': '\n'.join(
                chain(
                    [
                        dedent(description),
                    ],
                    (
                        f'- ``{err.__name__}`` - {errors[err] or err.__doc__}'  # noqa: WPS237
                        for err in errors_sieved[code]
                    ),
                )
            ),
            'model': error.ErrInfo if 400 <= code < 500 else None,  # noqa: PLR2004, WPS432
        }
        for code, description in descriptions.items()
    }
