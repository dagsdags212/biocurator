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


def test_make_retryer_creates_retrying_instance():
    """make_retryer returns a configured Retrying instance."""
    import logging
    from biocurator.config.schema import RetryConfig
    from biocurator.utils.retryable_exceptions import make_retryer

    cfg = RetryConfig(max_attempts=3, backoff_factor=2.0, max_delay=60, timeout=30)
    retryer = make_retryer(cfg, logging.getLogger("test"))

    assert retryer.stop.max_attempt_number == 3
    assert retryer.wait.multiplier == 2.0
    assert retryer.wait.max == 60
    assert retryer.reraise is True
