from unittest.mock import MagicMock, patch
from typer.testing import CliRunner
from biocurator.cli.main import app

runner = CliRunner()


def test_status_no_providers():
    """No providers configured → yellow warning, exit 0."""
    with (
        patch("biocurator.cli.commands.status.Biocurator") as mock_biocurator,
        patch("biocurator.cli.commands.status.ConfigLoader") as mock_loader,
    ):
        mock_instance = MagicMock()
        mock_instance.searchers = {}
        mock_biocurator.return_value = mock_instance
        mock_loader.load.return_value = MagicMock()

        result = runner.invoke(app, ["status", "--config", "dummy.yaml"])

        assert result.exit_code == 0
        assert "No database providers configured" in result.output


def test_status_single_up_provider():
    """Single UP provider → table with all columns, summary line."""
    with (
        patch("biocurator.cli.commands.status.Biocurator") as mock_biocurator,
        patch("biocurator.cli.commands.status.ConfigLoader") as mock_loader,
    ):
        mock_instance = MagicMock()
        mock_instance.searchers = {"ncbi": MagicMock()}
        mock_instance.get_health_status.return_value = [
            {
                "provider": "ncbi",
                "status": "UP",
                "response_time_ms": 150.0,
                "breaker_state": "closed",
                "error": None,
            }
        ]
        mock_biocurator.return_value = mock_instance
        mock_loader.load.return_value = MagicMock()

        result = runner.invoke(app, ["status", "--config", "dummy.yaml"])

        assert result.exit_code == 0
        assert "ncbi" in result.output
        assert "UP" in result.output
        assert "150ms" in result.output
        assert "closed" in result.output
        assert "1 reachable, 0 unreachable" in result.output


def test_status_mixed_providers():
    """Mixed UP/DOWN providers → both shown in table, combined summary."""
    with (
        patch("biocurator.cli.commands.status.Biocurator") as mock_biocurator,
        patch("biocurator.cli.commands.status.ConfigLoader") as mock_loader,
    ):
        mock_instance = MagicMock()
        mock_instance.searchers = {"ncbi": MagicMock(), "uniprot": MagicMock()}
        mock_instance.get_health_status.return_value = [
            {
                "provider": "ncbi",
                "status": "UP",
                "response_time_ms": 120.0,
                "breaker_state": "closed",
                "error": None,
            },
            {
                "provider": "uniprot",
                "status": "DOWN",
                "response_time_ms": 5000.0,
                "breaker_state": "open",
                "error": "Timeout",
            },
        ]
        mock_biocurator.return_value = mock_instance
        mock_loader.load.return_value = MagicMock()

        result = runner.invoke(app, ["status", "--config", "dummy.yaml"])

        assert result.exit_code == 0
        assert "ncbi" in result.output
        assert "uniprot" in result.output
        assert "UP" in result.output
        assert "DOWN" in result.output
        assert "1 reachable, 1 unreachable, 2 total providers" in result.output


def test_status_breaker_closed():
    """Breaker closed → green closed in table."""
    with (
        patch("biocurator.cli.commands.status.Biocurator") as mock_biocurator,
        patch("biocurator.cli.commands.status.ConfigLoader") as mock_loader,
    ):
        mock_instance = MagicMock()
        mock_instance.searchers = {"ncbi": MagicMock()}
        mock_instance.get_health_status.return_value = [
            {
                "provider": "ncbi",
                "status": "UP",
                "response_time_ms": 50.0,
                "breaker_state": "closed",
                "error": None,
            }
        ]
        mock_biocurator.return_value = mock_instance
        mock_loader.load.return_value = MagicMock()

        result = runner.invoke(app, ["status", "--config", "dummy.yaml"])

        assert result.exit_code == 0
        assert "closed" in result.output


def test_status_breaker_open():
    """Breaker open → red open in table."""
    with (
        patch("biocurator.cli.commands.status.Biocurator") as mock_biocurator,
        patch("biocurator.cli.commands.status.ConfigLoader") as mock_loader,
    ):
        mock_instance = MagicMock()
        mock_instance.searchers = {"ncbi": MagicMock()}
        mock_instance.get_health_status.return_value = [
            {
                "provider": "ncbi",
                "status": "DOWN",
                "response_time_ms": 0.0,
                "breaker_state": "open",
                "error": "Circuit open",
            }
        ]
        mock_biocurator.return_value = mock_instance
        mock_loader.load.return_value = MagicMock()

        result = runner.invoke(app, ["status", "--config", "dummy.yaml"])

        assert result.exit_code == 0
        assert "open" in result.output


def test_status_breaker_half_open():
    """Breaker half_open → yellow half_open in table."""
    with (
        patch("biocurator.cli.commands.status.Biocurator") as mock_biocurator,
        patch("biocurator.cli.commands.status.ConfigLoader") as mock_loader,
    ):
        mock_instance = MagicMock()
        mock_instance.searchers = {"ncbi": MagicMock()}
        mock_instance.get_health_status.return_value = [
            {
                "provider": "ncbi",
                "status": "UP",
                "response_time_ms": 75.0,
                "breaker_state": "half_open",
                "error": None,
            }
        ]
        mock_biocurator.return_value = mock_instance
        mock_loader.load.return_value = MagicMock()

        result = runner.invoke(app, ["status", "--config", "dummy.yaml"])

        assert result.exit_code == 0
        assert "half_open" in result.output


def test_status_breaker_none():
    """No breaker (breaker_state=None) → N/A in table."""
    with (
        patch("biocurator.cli.commands.status.Biocurator") as mock_biocurator,
        patch("biocurator.cli.commands.status.ConfigLoader") as mock_loader,
    ):
        mock_instance = MagicMock()
        mock_instance.searchers = {"ncbi": MagicMock()}
        mock_instance.get_health_status.return_value = [
            {
                "provider": "ncbi",
                "status": "UP",
                "response_time_ms": 40.0,
                "breaker_state": None,
                "error": None,
            }
        ]
        mock_biocurator.return_value = mock_instance
        mock_loader.load.return_value = MagicMock()

        result = runner.invoke(app, ["status", "--config", "dummy.yaml"])

        assert result.exit_code == 0
        assert "N/A" in result.output
