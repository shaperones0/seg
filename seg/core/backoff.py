"""Exponential backoff implementation."""

import asyncio
import math
from collections.abc import Awaitable, Callable
from functools import lru_cache, wraps
from logging import getLogger
from secrets import SystemRandom

from seg.core import error

logger = getLogger(__name__)


@lru_cache
def _get_system_random() -> SystemRandom:
    return SystemRandom()


def nrandom(u1: float | None = None, u2: float | None = None) -> float:
    """Return random number between 0 and 1 with normal distribution.

    The two parameters can be substituted with 2
    uniformly distributed random numbers.
    The answer is calculated according to the Box-Muller transform.

    :param u1: Uniformly distributed random number between
      0 and 1 or None for it to be generated in-place.
    :param u2: Uniformly distributed random number
      between 0 and 1 or None for it to be generated in-place.
    :return: Normally distributed random number.
    """
    rng = _get_system_random()

    if u1 is None:
        u1 = rng.random()
    if u2 is None:
        u2 = rng.random()

    return math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)  # noqa: WPS221


class Backoff:
    """Exponential backoff implementation."""

    def __init__(self, service_name: str) -> None:
        """Initialize backoff manager.

        :param service_name: Service name.
        """
        self.service_name = service_name

    def __call__[  # noqa: WPS211,WPS234
        **T_og_params,
        T_og_ret,
    ](
        self,
        *exceptions: error.ErrType,
        start_sleep_time: float = 0.1,
        factor: float = 2.0,
        max_sleep_time: float = 10.0,
        jitter: float = 0.1,
        max_retries: int = 30,
    ) -> Callable[
        [Callable[T_og_params, Awaitable[T_og_ret]]],
        Callable[T_og_params, Awaitable[T_og_ret]],
    ]:
        """Make function retry itself if it raises an exception.

        Decorated function is relaunched with increasing time intervals between
        launches until it runs with no errors thrown, or the maximum number of
        retries is exceeded, in which case an error is thrown.

        :param exceptions: Exceptions to catch.
        :param start_sleep_time: Initial delay after
          the first unsuccessful attempt, in ms.
        :param factor: By how much to multiply the
          delay after each unsuccessful attempt.
        :param max_sleep_time: Maximum delay, in ms.
        :param jitter: By how much to alter the time after
          each unsuccessful attempt.
        :param max_retries: The maximum number of retries
          after which an exception is raised.
        :return: Decorated function.
        :raises BackoffError: Exceeded maximum number of retries.
        """

        def decorator(
            func: Callable[T_og_params, Awaitable[T_og_ret]],
        ) -> Callable[T_og_params, Awaitable[T_og_ret]]:
            @wraps(func)
            async def wrapper(
                *args: T_og_params.args, **kwargs: T_og_params.kwargs
            ) -> T_og_ret:
                delay = start_sleep_time
                retries = 0
                while True:
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as ex:
                        exc = ex
                    exc_name = exc.__class__.__name__ if exc else ''

                    # error happened, check if exceed max retries
                    if retries >= max_retries:
                        logger.error(
                            '%s exceeded max retries (%d).',
                            self.service_name,
                            max_retries,
                        )
                        raise error.BackoffError(self.service_name)
                    retries += 1

                    # pause between requests
                    logger.warning(
                        '%s timeout #%d (%s). Retrying in %s',
                        self.service_name,
                        retries,
                        exc_name,
                        delay,
                    )
                    await asyncio.sleep(delay)

                    # calculate next delay
                    delay = min(delay * factor, max_sleep_time)
                    delay += nrandom() * delay * jitter

            return wrapper

        return decorator
