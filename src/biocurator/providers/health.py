import time
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    provider: str
    reachable: bool
    response_time_ms: float = 0.0
    error: str | None = None


class HealthChecker:
    @staticmethod
    def ping_ncbi(timeout: int = 30) -> HealthStatus:
        from Bio import Entrez
        from Bio.Entrez.Parser import DictionaryElement

        start = time.monotonic()
        try:
            Entrez.email = "health-check@biocurator"
            handle = Entrez.esearch(db="nuccore", term="a[organism]", retmax=1)
            result: DictionaryElement = Entrez.read(handle)
            handle.close()
            elapsed = (time.monotonic() - start) * 1000
            _ = result.get("IdList", [])
            return HealthStatus(
                provider="ncbi", reachable=True, response_time_ms=round(elapsed, 1)
            )
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            return HealthStatus(
                provider="ncbi",
                reachable=False,
                response_time_ms=round(elapsed, 1),
                error=str(exc),
            )

    @staticmethod
    def ping_uniprot(timeout: int = 30) -> HealthStatus:
        import requests

        start = time.monotonic()
        try:
            response = requests.get(
                "https://rest.uniprot.org/uniprotkb/search",
                params={"query": "a", "size": 1},
                timeout=timeout,
            )
            response.raise_for_status()
            elapsed = (time.monotonic() - start) * 1000
            return HealthStatus(
                provider="uniprot", reachable=True, response_time_ms=round(elapsed, 1)
            )
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            return HealthStatus(
                provider="uniprot",
                reachable=False,
                response_time_ms=round(elapsed, 1),
                error=str(exc),
            )
