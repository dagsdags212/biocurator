from unittest.mock import patch
from Bio import Entrez
from biocurator.providers.base import DatabaseConfig
from biocurator.providers.ncbi import NCBISearcher


def test_api_key_is_set_on_entrez_when_provided():
    config = DatabaseConfig(name="NCBI", api_key="testkey123")
    with patch.object(Entrez, "api_key", None, create=True):
        NCBISearcher(config, "test@example.com")
        assert Entrez.api_key == "testkey123"


def test_api_key_not_set_when_absent():
    config = DatabaseConfig(name="NCBI", api_key=None)
    original = Entrez.api_key
    NCBISearcher(config, "test@example.com")
    assert Entrez.api_key == original
