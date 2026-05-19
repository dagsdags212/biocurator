from dataclasses import dataclass

from biocurator.providers.base import SearchCriteria


@dataclass
class UniProtSearchCriteria(SearchCriteria):
    reviewed: bool | None = None
