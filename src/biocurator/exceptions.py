"""
Biocurator customer exceptions.
"""


class BiocuratorError(Exception):
    """Base exception for all biocurator errors."""


class ConfigNotFoundError(BiocuratorError):
    """Config file path does not exist."""


class InvalidConfigError(BiocuratorError):
    """YAML is malformed or fails schema validation."""


class JobNotFoundError(BiocuratorError):
    """--jobs references a job name not defined in config."""


class DatabaseSearchError(BiocuratorError):
    """Search API call to a remote database failed."""


class DownloadError(BiocuratorError):
    """Sequence download from a remote database failed."""


class ExportError(BiocuratorError):
    """Writing output files to disk failed."""
