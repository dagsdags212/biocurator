import socket
import urllib.error

import requests
from tenacity import retry_if_exception_type

RETRYABLE_EXCEPTIONS = (
    urllib.error.URLError,
    urllib.error.HTTPError,
    requests.ConnectionError,
    requests.Timeout,
    requests.HTTPError,
    socket.timeout,
    socket.gaierror,
)

RETRYABLE_PREDICATE = retry_if_exception_type(RETRYABLE_EXCEPTIONS)


def _is_retryable_http_error(exc: Exception) -> bool:
    if isinstance(exc, requests.HTTPError):
        return exc.response is not None and exc.response.status_code >= 500
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code >= 500
    return False
