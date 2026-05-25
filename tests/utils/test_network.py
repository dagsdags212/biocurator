import socket
import urllib.error

import requests

from biocurator.utils.retryable_exceptions import _is_retryable


def test_retryable_connection_error():
    assert _is_retryable(requests.ConnectionError())


def test_retryable_timeout():
    assert _is_retryable(requests.Timeout())


def test_retryable_socket_timeout():
    assert _is_retryable(socket.timeout())


def test_retryable_gaierror():
    assert _is_retryable(socket.gaierror())


def test_retryable_urlerror():
    assert _is_retryable(urllib.error.URLError("host not found"))


def test_retryable_http_500():
    response = requests.Response()
    response.status_code = 500
    assert _is_retryable(requests.HTTPError(response=response))


def test_retryable_http_503():
    response = requests.Response()
    response.status_code = 503
    assert _is_retryable(requests.HTTPError(response=response))


def test_not_retryable_http_400():
    response = requests.Response()
    response.status_code = 400
    assert not _is_retryable(requests.HTTPError(response=response))


def test_not_retryable_http_404():
    response = requests.Response()
    response.status_code = 404
    assert not _is_retryable(requests.HTTPError(response=response))


def test_not_retryable_value_error():
    assert not _is_retryable(ValueError("bad data"))


def test_not_retryable_key_error():
    assert not _is_retryable(KeyError("missing"))
