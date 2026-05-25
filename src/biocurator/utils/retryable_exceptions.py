import socket
import urllib.error

import requests
from tenacity import retry_if_exception


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
