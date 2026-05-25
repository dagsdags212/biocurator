from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Generic, TypeVar, Iterator

from biocurator.config.schema import BreakerConfig, RetryConfig


class NCBIDatabase(str, Enum):
    # Literature & References
    PUBMED = "pubmed"
    PMC = "pmc"
    BOOKS = "books"
    NLM_CATALOG = "nlmcatalog"
    MESH = "mesh"

    # Nucleotide & Genome Sequences
    NUCCORE = "nuccore"
    NUCLEOTIDE = "nucleotide"
    GENOME = "genome"
    ASSEMBLY = "assembly"
    ANNOT_INFO = "annotinfo"
    SEQ_ANNOT = "seqannot"
    SRA = "sra"

    # Protein & Structure
    PROTEIN = "protein"
    IPG = "ipg"
    PROTEIN_CLUSTERS = "proteinclusters"
    PROT_FAM = "protfam"
    STRUCTURE = "structure"
    CDD = "cdd"

    # Genes & Variation
    GENE = "gene"
    SNP = "snp"
    DBVAR = "dbvar"
    CLINVAR = "clinvar"
    GAP = "gap"
    GAP_PLUS = "gapplus"

    # Chemical & Bioassay
    PC_COMPOUND = "pccompound"
    PC_SUBSTANCE = "pcsubstance"
    PC_ASSAY = "pcassay"

    # Expression & Functional Genomics
    GDS = "gds"
    GEO_PROFILES = "geoprofiles"
    GRASP = "grasp"

    # Taxonomy & Organisms
    TAXONOMY = "taxonomy"
    BIOCOLLECTIONS = "biocollections"
    ORG_TRACK = "orgtrack"

    # Clinical & Medical Genetics
    OMIM = "omim"
    MED_GEN = "medgen"
    GTR = "gtr"

    # Projects & Metadata
    BIOPROJECT = "bioproject"
    BIOSAMPLE = "biosample"
    BLAST_DB_INFO = "blastdbinfo"


T = TypeVar("T", bound="SearchCriteria")
C = TypeVar("C", bound="SearchCriteria")


@dataclass
class SearchCriteria:
    organism: str | None = None
    keywords: list[str] = field(default_factory=list)
    min_length: int | None = None
    max_length: int | None = None
    start_date: str | None = None
    end_date: str | None = None
    max_results: int = 100
    exclude_terms: list[str] = field(default_factory=list)
    quality_threshold: float | None = None


class QueryBuilder(ABC, Generic[T]):
    @abstractmethod
    def build(self, criteria: T) -> str:
        """Translate SearchCriteria into a database-specific query string."""

    @abstractmethod
    def available_fields(self) -> dict[str, str]:
        """Return a mapping of supported field names to their descriptions."""


@dataclass
class DatabaseConfig:
    name: str
    base_url: str | None = None
    api_key: str | None = None
    rate_limit: float = 0.3
    batch_size: int = 20
    timeout: int = 30
    retry: RetryConfig | None = None
    breaker: BreakerConfig | None = None


@dataclass
class SequenceRecord:
    id: str
    accession: str
    database: str
    title: str = ""
    organism: str = ""
    sequence_length: int = 0
    sequence: str | None = None
    description: str = ""
    create_date: str = ""
    update_date: str = ""
    taxonomy_id: str = ""
    authors: str = ""
    journal: str = ""
    downloaded: bool = False
    quality_score: float | None = None


class DatabaseSearcher(ABC, Generic[C]):
    def __init__(self, config: DatabaseConfig, email: str) -> None:
        self.config = config
        self.email = email

    @abstractmethod
    def build_query(self, criteria: C) -> str:
        """Translate SearchCriteria into a database-specific query string."""

    @abstractmethod
    def search(self, criteria: C) -> list[str]:
        """Query the database and return a list of record IDs."""

    @abstractmethod
    def fetch_metadata(
        self, ids: list[str], criteria: C | None = None
    ) -> Iterator[SequenceRecord]:
        """Retrieve metadata for a set of IDs."""

    @abstractmethod
    def download(
        self, ids: list[str], outdir: Path, criteria: C | None = None
    ) -> Iterator[SequenceRecord]:
        """Download sequences and return associated metadata."""
