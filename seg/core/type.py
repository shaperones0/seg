from typing import Any


def scast[T](typ: type[T], val: Any) -> T:
    if not isinstance(val, typ):
        msg = f"{val} is not {typ}"
        raise TypeError(msg)
    return val
