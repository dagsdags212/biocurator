from biocurator.providers.base import QueryBuilder
from biocurator.providers.uniprot.criteria import UniProtSearchCriteria


class UniProtQueryBuilder(QueryBuilder[UniProtSearchCriteria]):
    def build(self, criteria: UniProtSearchCriteria) -> str:
        parts = []
        if criteria.organism:
            parts.append(f'organism:"{criteria.organism}"')
        if criteria.keywords:
            parts.append("(" + " OR ".join(criteria.keywords) + ")")
        if criteria.min_length:
            parts.append(f"length:[{criteria.min_length} TO *]")
        if criteria.max_length:
            parts.append(f"length:[* TO {criteria.max_length}]")
        if criteria.reviewed is not None:
            parts.append(f"reviewed:{'true' if criteria.reviewed else 'false'}")
        return " AND ".join(parts)

    def available_fields(self) -> dict[str, str]:
        return {
            "accession": "UniProtKB accession number",
            "id": "UniProtKB entry name",
            "organism_name": "Scientific name of the organism",
            "organism_id": "NCBI taxonomy identifier",
            "gene_names": "Gene name(s)",
            "protein_name": "Recommended protein name",
            "length": "Sequence length in amino acids",
            "reviewed": "Reviewed (Swiss-Prot) or unreviewed (TrEMBL)",
            "keyword": "UniProt controlled vocabulary keyword",
            "go": "Gene Ontology term",
            "ec": "Enzyme Commission number",
            "ft_sites": "Annotated sites (active site, binding site, etc.)",
            "database": "Cross-references to external databases",
            "date_created": "Date the entry was created",
            "date_modified": "Date the entry was last modified",
            "date_sequence_modified": "Date the sequence was last modified",
            "mass": "Molecular mass in Daltons",
            "cc_subcellular_location": "Subcellular location",
            "cc_tissue_specificity": "Tissue specificity",
            "cc_disease": "Disease involvement",
            "taxonomy_id": "Taxonomic lineage identifier",
            "lineage": "Full taxonomic lineage",
            "strain": "Organism strain",
            "fragment": "Whether sequence is a fragment",
        }
