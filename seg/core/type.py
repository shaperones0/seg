"""Typing shenanigans."""

from typing import Any


def scast[T_target](typ: type[T_target], val: Any) -> T_target:  # noqa: WPS110
    """Cast a type into another type with `isinstance` checking.

    :param typ: Target type.
    :param val: Value to cast.
    :return: The same unaltered value.
    """
    if not isinstance(val, typ):
        msg = f'{val} is not {typ}'
        raise TypeError(msg)
    return val
