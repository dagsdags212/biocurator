import logging
import socket
import urllib.error

import requests
from tenacity import (
    Retrying,
    before_sleep_log,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from biocurator.config.schema import RetryConfig


def _is_retryable(exc: Exception) -> bool:
    """Return True if exc is a retryable network error.

    Retryable categories:
    - Network-level: ConnectionError, Timeout, DNS errors
    - Server-side HTTP errors: 5xx only (4xx is never retryable)
    """
    if isinstance(exc, (requests.HTTPError, urllib.error.HTTPError)):
        if isinstance(exc, requests.HTTPError):
            return exc.response is not None and exc.response.status_code >= 500
        return exc.code >= 500
    return isinstance(
        exc,
        (
            requests.ConnectionError,
            requests.Timeout,
            urllib.error.URLError,
            socket.timeout,
            socket.gaierror,
        ),
    )


RETRYABLE_PREDICATE = retry_if_exception(_is_retryable)


def make_retryer(retry_config: RetryConfig, logger: logging.Logger) -> Retrying:
    """Create a tenacity Retrying instance configured with retryable-exception predicate.

    Parameters
    ----------
    retry_config : RetryConfig
        Resolved retry configuration (max_attempts, backoff_factor, max_delay).
    logger : logging.Logger
        Logger used for before-sleep warning messages between retry attempts.

    Returns
    -------
    Retrying
        Configured retryer instance.
    """
    return Retrying(
        stop=stop_after_attempt(retry_config.max_attempts),
        wait=wait_exponential(
            multiplier=retry_config.backoff_factor,
            max=retry_config.max_delay,
        ),
        retry=RETRYABLE_PREDICATE,
        reraise=True,
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
