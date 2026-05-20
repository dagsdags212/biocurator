"""
Network Utilities
=================

This module provides utilities for network-bound operations,
including retry logic and request handling.


© Jan Emmanuel Samson (2026-)
"""

import time
import functools
import random
from typing import Callable, Type, Tuple, Any
from biocurator.utils.logging import get_logger

logger = get_logger(__name__)


def retry(
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
) -> Callable:
    """Decorator for retrying a function with exponential backoff.

    Parameters
    ----------
    exceptions : Tuple[Type[Exception], ...]
        The exceptions that should trigger a retry.
    max_attempts : int
        Maximum number of attempts before giving up.
    initial_delay : float
        Initial delay between retries in seconds.
    backoff_factor : float
        Factor by which the delay increases after each attempt.
    jitter : bool
        Whether to add random jitter to the delay.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                func_name = getattr(func, "__name__", str(func))
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(
                            f"Max attempts ({max_attempts}) reached for {func_name}. "
                            f"Final error: {e}"
                        )
                        break

                    wait_time = delay
                    if jitter:
                        wait_time *= random.uniform(0.5, 1.5)

                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func_name}: {e}. "
                        f"Retrying in {wait_time:.2f}s..."
                    )

                    time.sleep(wait_time)
                    delay *= backoff_factor

            if last_exception:
                raise last_exception

        return wrapper

    return decorator
