from collections.abc import Callable, Awaitable
from functools import wraps, lru_cache
from logging import getLogger
from secrets import SystemRandom
import math
import asyncio

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

    return math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)


def backoff(
    start_sleep_time: float = 0.1,
    factor: float = 2.0,
    max_sleep_time: float = 10.0,
    jitter: float = 0.1,
    max_retries: int = 30,
) -> Callable:
    """Make function retry itself if it returns False.

    Decorated function is relaunched with increasing
    time intervals between launches until it returns
    True or the maximum number
    of retries is exceeded, on which an error is thrown.

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

    def decorator[**og_params](
            func: Callable[og_params, Awaitable[bool]]
    ) -> Callable[og_params, Awaitable[None]]:
        @wraps(func)
        async def wrapper(
                *args: og_params.args,
                **kwargs: og_params.kwargs
        ) -> None:
            delay = start_sleep_time
            retries = 0
            while True:
                if func(*args, **kwargs):
                    # OK, got a response
                    break

                # error happened, check if exceed max retries
                if retries >= max_retries:
                    raise error.BackoffError(func.__name__, retries)
                retries += 1

                # pause between requests
                logger.warning(
                    "%s timeout. Retrying in %s",
                    func.__name__, delay
                )
                await asyncio.sleep(delay)

                # calculate next delay
                delay = min(delay * factor, max_sleep_time)
                delay += nrandom() * delay * jitter

        return wrapper

    return decorator
