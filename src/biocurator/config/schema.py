from dataclasses import dataclass, field


@dataclass
class SearchConfig:
    databases: list[str]
    organism: str | None = None
    sequence_type: str = "nucleotide"
    keywords: list[str] = field(default_factory=list)
    max_results: int = 100
    date_range: dict | None = None
    exclude_terms: list[str] = field(default_factory=list)
    location: str | None = None
    taxonomy_filter: str | None = None


@dataclass
class FilterConfig:
    min_length: int | None = None
    max_length: int | None = None
    exclude_terms: list[str] = field(default_factory=list)
    quality_threshold: float | None = None


@dataclass
class ExportConfig:
    outdir: str = "results"
    formats: list[str] = field(default_factory=lambda: ["fasta"])
    prefix: str = "biocurator"


@dataclass
class JobConfig:
    name: str
    search: SearchConfig
    filter: FilterConfig
    export: ExportConfig


@dataclass
class GlobalConfig:
    email: str
    jobs: list[JobConfig]
