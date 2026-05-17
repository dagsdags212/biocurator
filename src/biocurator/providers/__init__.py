from biocurator.providers.base import DatabaseConfig, DatabaseSearcher, SearchCriteria
from biocurator.providers.registry import ProviderRegistry

import biocurator.providers.ncbi      # registers "ncbi"
import biocurator.providers.uniprot   # registers "uniprot"

__all__ = ["DatabaseConfig", "DatabaseSearcher", "SearchCriteria", "ProviderRegistry"]
