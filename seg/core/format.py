"""Swagger doc formatting helpers."""

from collections.abc import Mapping
from typing import Any
from itertools import chain
from textwrap import dedent

from seg.core.error import RequestError


def responses(
        *,
        errors: dict[type[RequestError], str | None],
        descriptions: Mapping[int, str],

) -> dict[int, dict[str, Any]]:
    errors_sieved: dict[int, list[type[RequestError]]] = {}
    for err in errors:
        errors_sieved.setdefault(err.status_code, []).append(err)

    return {
        code: {
            "description": "\n".join(chain(
                [
                    dedent(description),
                    "Errors:",
                ],
                (
                    f"- ``{err.__name__}`` - {errors[err] or err.__doc__}"
                    for err
                    in errors_sieved[code]
                )
            ))
        }
        for code, description in descriptions.items()
    }
