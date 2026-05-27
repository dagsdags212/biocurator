import time
import pytest
from unittest.mock import MagicMock, patch
from biocurator.providers.health import HealthChecker, HealthStatus


class TestHealthChecker:
    """D-04 targets: ping_ncbi() and ping_uniprot()."""

    @patch("Bio.Entrez.read")
    @patch("Bio.Entrez.esearch")
    def test_ping_ncbi_reachable(self, mock_esearch, mock_read):
        """ping_ncbi returns reachable=True when Entrez.esearch succeeds."""
        mock_handle = MagicMock()
        mock_esearch.return_value = mock_handle
        mock_read.return_value = {"IdList": ["123"]}

        result = HealthChecker.ping_ncbi(timeout=30)

        assert result.provider == "ncbi"
        assert result.reachable is True
        assert result.response_time_ms > 0
        assert result.error is None

    @patch("biocurator.providers.health.time.monotonic")
    @patch("Bio.Entrez.esearch")
    def test_ping_ncbi_unreachable(self, mock_esearch, mock_time):
        """ping_ncbi returns reachable=False with error when Entrez raises."""
        mock_time.side_effect = [1000.0, 1001.5]  # start=1000, end=1001.5 → 1.5ms
        mock_esearch.side_effect = Exception("Connection refused")

        result = HealthChecker.ping_ncbi(timeout=30)

        assert result.provider == "ncbi"
        assert result.reachable is False
        assert result.response_time_ms > 0
        assert result.error == "Connection refused"

    @patch("requests.get")
    @patch("biocurator.providers.health.time.monotonic")
    def test_ping_uniprot_reachable(self, mock_time, mock_get):
        """ping_uniprot returns reachable=True when requests.get returns 200."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        mock_time.side_effect = [1000.0, 1001.2]  # start=1000, end=1001.2 → 1.2ms

        result = HealthChecker.ping_uniprot(timeout=30)

        assert result.provider == "uniprot"
        assert result.reachable is True
        assert result.response_time_ms > 0
        assert result.error is None

    @patch("requests.get")
    @patch("biocurator.providers.health.time.monotonic")
    def test_ping_uniprot_unreachable(self, mock_time, mock_get):
        """ping_uniprot returns reachable=False with error when requests.get raises."""
        mock_get.side_effect = Exception("Timeout")
        mock_time.side_effect = [1000.0, 1001.8]  # start=1000, end=1001.8 → 1.8ms

        result = HealthChecker.ping_uniprot(timeout=30)

        assert result.provider == "uniprot"
        assert result.reachable is False
        assert result.response_time_ms > 0
        assert result.error == "Timeout"
