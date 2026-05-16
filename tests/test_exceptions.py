import pytest
from biocurator.exceptions import (
    BiocuratorError,
    ConfigNotFoundError,
    InvalidConfigError,
    JobNotFoundError,
    DatabaseSearchError,
    DownloadError,
    ExportError,
)


def test_all_exceptions_are_biocurator_errors():
    for cls in [
        ConfigNotFoundError,
        InvalidConfigError,
        JobNotFoundError,
        DatabaseSearchError,
        DownloadError,
        ExportError,
    ]:
        assert issubclass(cls, BiocuratorError)


def test_exceptions_carry_message():
    exc = InvalidConfigError("bad field")
    assert "bad field" in str(exc)


def test_exceptions_are_catchable_as_base():
    with pytest.raises(BiocuratorError):
        raise ConfigNotFoundError("config.yaml not found")
