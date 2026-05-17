from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SearchCriteria:
    organism: str | None = None
    sequence_type: str = "nucleotide"
    keywords: list[str] = field(default_factory=list)
    location: str | None = None
    min_length: int | None = None
    max_length: int | None = None
    start_date: str | None = None
    end_date: str | None = None
    max_results: int = 100
    exclude_terms: list[str] = field(default_factory=list)
    taxonomy_filter: str | None = None
    quality_threshold: float | None = None


@dataclass
class DatabaseConfig:
    name: str
    base_url: str | None = None
    api_key: str | None = None
    rate_limit: float = 0.3
    batch_size: int = 20
    timeout: int = 30


class DatabaseSearcher(ABC):
    def __init__(self, config: DatabaseConfig, email: str) -> None:
        import requests
        self.config = config
        self.email = email
        self.session = requests.Session()

    @abstractmethod
    def build_query(self, criteria: SearchCriteria) -> str:
        """Translate SearchCriteria into a database-specific query string."""

    @abstractmethod
    def search(self, criteria: SearchCriteria) -> list[str]:
        """Query the database and return a list of record IDs."""

    @abstractmethod
    def fetch_metadata(self, ids: list[str]) -> list[dict[str, Any]]:
        """Retrieve metadata for a set of IDs."""

    @abstractmethod
    def download(self, ids: list[str], outdir: Path) -> list[dict[str, Any]]:
        """Download sequences and return associated metadata."""
