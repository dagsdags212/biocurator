import pytest
from unittest.mock import MagicMock, patch
from biocurator.utils.network import retry


def test_retry_success():
    mock_func = MagicMock(return_value="success")
    decorated = retry(max_attempts=3)(mock_func)
    
    assert decorated() == "success"
    assert mock_func.call_count == 1


def test_retry_eventual_success():
    mock_func = MagicMock(side_effect=[ValueError("fail"), "success"])
    # Set delays to 0 for fast testing
    decorated = retry(exceptions=(ValueError,), max_attempts=3, initial_delay=0.01)(mock_func)
    
    assert decorated() == "success"
    assert mock_func.call_count == 2


def test_retry_max_attempts_reached():
    mock_func = MagicMock(side_effect=ValueError("fail"))
    decorated = retry(exceptions=(ValueError,), max_attempts=3, initial_delay=0.01)(mock_func)
    
    with pytest.raises(ValueError, match="fail"):
        decorated()
    
    assert mock_func.call_count == 3


def test_retry_unhandled_exception():
    mock_func = MagicMock(side_effect=KeyError("unhandled"))
    decorated = retry(exceptions=(ValueError,), max_attempts=3, initial_delay=0.01)(mock_func)
    
    with pytest.raises(KeyError, match="unhandled"):
        decorated()
    
    # Should not retry if exception type doesn't match
    assert mock_func.call_count == 1
