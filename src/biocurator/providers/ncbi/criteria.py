from dataclasses import dataclass

from biocurator.providers.base import NCBIDatabase, SearchCriteria


@dataclass
class NCBISearchCriteria(SearchCriteria):
    database: NCBIDatabase = NCBIDatabase.NUCCORE
    taxonomy_filter: str | None = None
    location: str | None = None
    webenv: str | None = None
    query_key: str | None = None
