from biocurator.providers.base import NCBIDatabase, QueryBuilder
from biocurator.providers.ncbi.criteria import NCBISearchCriteria


class SequenceQueryBuilder(QueryBuilder[NCBISearchCriteria]):
    def build(self, criteria: NCBISearchCriteria) -> str:
        parts = []
        if criteria.organism:
            parts.append(f'"{criteria.organism}"[Organism]')
        if criteria.keywords:
            parts.append(" OR ".join(f'"{kw}"' for kw in criteria.keywords))
        if criteria.location:
            loc_terms = [f'"{t.strip()}"' for t in criteria.location.split(",")]
            parts.append(" OR ".join(loc_terms))
        if criteria.min_length and criteria.max_length:
            parts.append(f"{criteria.min_length}:{criteria.max_length}[Sequence Length]")
        elif criteria.min_length:
            parts.append(f"{criteria.min_length}:999999999[Sequence Length]")
        elif criteria.max_length:
            parts.append(f"1:{criteria.max_length}[Sequence Length]")
        if criteria.start_date and criteria.end_date:
            parts.append(
                f'"{criteria.start_date}"[Publication Date]:"{criteria.end_date}"[Publication Date]'
            )
        if criteria.taxonomy_filter:
            parts.append(f'"{criteria.taxonomy_filter}"[Organism]')
        for term in criteria.exclude_terms:
            parts.append(f'NOT "{term}"')
        return " AND ".join(parts)

    def available_fields(self) -> dict[str, str]:
        return {
            "ALL": "All terms from all searchable fields",
            "UID": "Unique number assigned to each sequence",
            "FILT": "Limits the records",
            "WORD": "Free text associated with record",
            "TITL": "Words in definition line",
            "KYWD": "Nonstandardized terms provided by submitter",
            "AUTH": "Author(s) of publication",
            "JOUR": "Journal abbreviation of publication",
            "ORGN": "Scientific and common names of organisms and taxonomy",
            "ACCN": "Accession number of sequence",
            "PACC": "Does not include retired secondary accessions",
            "GENE": "Name of gene associated with sequence",
            "PROT": "Name of protein associated with sequence",
            "ECNO": "EC number for enzyme or CAS registry number",
            "PDAT": "Date sequence added to GenBank",
            "MDAT": "Date of last update",
            "SLEN": "Length of sequence",
            "FKEY": "Feature annotated on sequence",
            "PORG": "Scientific and common names of primary organisms",
            "ASSM": "Assembly",
            "DIV": "Division",
            "STRN": "Strain",
            "ISOL": "Isolate",
            "CULT": "Cultivar",
            "BRD": "Breed",
            "GPRJ": "BioProject",
            "BIOS": "BioSample",
        }


class LiteratureQueryBuilder(QueryBuilder[NCBISearchCriteria]):
    def build(self, criteria: NCBISearchCriteria) -> str:
        parts = []
        if criteria.organism:
            parts.append(f'"{criteria.organism}"[MeSH Terms]')
        if criteria.keywords:
            parts.extend(f'"{kw}"[Title/Abstract]' for kw in criteria.keywords)
        if criteria.start_date and criteria.end_date:
            parts.append(
                f'"{criteria.start_date}"[Date - Publication]:"{criteria.end_date}"[Date - Publication]'
            )
        for term in criteria.exclude_terms:
            parts.append(f'NOT "{term}"')
        return " AND ".join(parts)

    def available_fields(self) -> dict[str, str]:
        return {
            "ALL": "All terms from all searchable fields",
            "UID": "Unique number assigned to publication",
            "FILT": "Limits the records",
            "TITL": "Words in title of publication",
            "MESH": "Medical Subject Headings assigned to publication",
            "MAJR": "MeSH terms of major importance to publication",
            "JOUR": "Journal abbreviation of publication",
            "AFFL": "Author's institutional affiliation and address",
            "TIAB": "Free text associated with Abstract/Title",
            "PDAT": "Date of publication",
            "EDAT": "Date publication first accessible through Entrez",
            "PTYP": "Type of publication (e.g., review)",
            "LANG": "Language of publication",
            "FAUT": "First Author of publication",
            "LAUT": "Last Author of publication",
            "GRNT": "NIH Grant Numbers",
            "MDAT": "Date of last modification",
            "WORD": "Free text associated with publication",
        }


class GeneQueryBuilder(QueryBuilder[NCBISearchCriteria]):
    def build(self, criteria: NCBISearchCriteria) -> str:
        parts = []
        if criteria.organism:
            parts.append(f'"{criteria.organism}"[Organism]')
        if criteria.keywords:
            parts.extend(f'"{kw}"[Gene/Protein Name]' for kw in criteria.keywords)
        if criteria.start_date and criteria.end_date:
            parts.append(
                f'"{criteria.start_date}"[Modification Date]:"{criteria.end_date}"[Modification Date]'
            )
        if criteria.taxonomy_filter:
            parts.append(f'"{criteria.taxonomy_filter}"[Organism]')
        for term in criteria.exclude_terms:
            parts.append(f'NOT "{term}"')
        return " AND ".join(parts)

    def available_fields(self) -> dict[str, str]:
        return {
            "ALL": "All terms from all searchable fields",
            "UID": "Unique number assigned to a gene record",
            "FILT": "Limits the records",
            "TITL": "Gene or protein name",
            "WORD": "Free text associated with record",
            "ORGN": "Scientific and common names of organism",
            "MDAT": "The last date on which the record was updated",
            "CHR": "Chromosome number or numbers",
            "MV": "Chromosomal map location as displayed in MapViewer",
            "GENE": "Symbol or symbols of the gene",
            "ECNO": "EC number for enzyme or CAS registry number",
            "MIM": "MIM number from OMIM",
            "DIS": "Name(s) of diseases associated with this gene",
            "ACCN": "Nucleotide or protein accession(s) associated with gene",
            "GO": "Gene Ontology",
            "DOM": "Domain Name",
            "GFN": "Gene full name",
            "PFN": "Protein full name",
            "GL": "Gene length",
            "XC": "Exon count",
            "EXPR": "Gene expression",
            "TID": "Taxonomy id",
        }


class SRAQueryBuilder(QueryBuilder[NCBISearchCriteria]):
    def build(self, criteria: NCBISearchCriteria) -> str:
        parts = []
        if criteria.organism:
            parts.append(f'"{criteria.organism}"[Organism]')
        if criteria.keywords:
            parts.extend(f'"{kw}"[All Fields]' for kw in criteria.keywords)
        if criteria.start_date and criteria.end_date:
            parts.append(
                f'"{criteria.start_date}"[Publication Date]:"{criteria.end_date}"[Publication Date]'
            )
        if criteria.taxonomy_filter:
            parts.append(f'"{criteria.taxonomy_filter}"[Organism]')
        for term in criteria.exclude_terms:
            parts.append(f'NOT "{term}"')
        return " AND ".join(parts)

    def available_fields(self) -> dict[str, str]:
        return {
            "ALL": "All terms from all searchable fields",
            "UID": "Unique number assigned to each SRA run",
            "FILT": "Limits the records",
            "ACCN": "Accession number of sequence",
            "TITL": "Words in definition line",
            "WORD": "Free text associated with record",
            "ORGN": "Scientific and common names of organism and taxonomy levels",
            "AUTH": "Author(s) of publication",
            "PDAT": "Date sequence added to GenBank",
            "MDAT": "Date of last update",
            "GPRJ": "BioProject",
            "BSPL": "BioSample",
            "PLAT": "Platform",
            "STRA": "Strategy",
            "SRC": "Source",
            "SEL": "Selection",
            "LAY": "Layout",
            "RLEN": "Read length",
            "ACS": "Access is public or controlled",
            "ALN": "Percent of aligned reads",
            "MBS": "Size in megabases",
        }


class TaxonomyQueryBuilder(QueryBuilder[NCBISearchCriteria]):
    def build(self, criteria: NCBISearchCriteria) -> str:
        parts = []
        if criteria.organism:
            parts.append(f'"{criteria.organism}"[Scientific Name]')
        if criteria.keywords:
            parts.extend(f'"{kw}"[All Fields]' for kw in criteria.keywords)
        for term in criteria.exclude_terms:
            parts.append(f'NOT "{term}"')
        return " AND ".join(parts)

    def available_fields(self) -> dict[str, str]:
        return {
            "ALL": "All terms from all searchable fields",
            "UID": "Taxonomy ID",
            "FILT": "Limits the records",
            "SCIN": "Scientific name of organism",
            "COMN": "Common name of organism",
            "TXSY": "Synonym of organism name",
            "ALLN": "All aliases for organism",
            "NXLV": "Immediate parent in taxonomic hierarchy",
            "SBTR": "Any parent node in taxonomic hierarchy",
            "LNGE": "Lineage in taxonomic hierarchy",
            "GC": "Nuclear genetic code",
            "MGC": "Mitochondrial genetic code",
            "PGC": "Plastid genetic code",
            "TXDV": "GenBank division",
            "RANK": "Hierarchical position (e.g., order, genus)",
            "MDAT": "Date of last update",
            "WORD": "Free text associated with record",
        }


_BUILDER_MAP: dict[NCBIDatabase, QueryBuilder[NCBISearchCriteria]] = {
    NCBIDatabase.NUCCORE: SequenceQueryBuilder(),
    NCBIDatabase.NUCLEOTIDE: SequenceQueryBuilder(),
    NCBIDatabase.PROTEIN: SequenceQueryBuilder(),
    NCBIDatabase.IPG: SequenceQueryBuilder(),
    NCBIDatabase.SRA: SRAQueryBuilder(),
    NCBIDatabase.PUBMED: LiteratureQueryBuilder(),
    NCBIDatabase.PMC: LiteratureQueryBuilder(),
    NCBIDatabase.GENE: GeneQueryBuilder(),
    NCBIDatabase.TAXONOMY: TaxonomyQueryBuilder(),
}


def get_builder(db: NCBIDatabase) -> QueryBuilder[NCBISearchCriteria]:
    builder = _BUILDER_MAP.get(db)
    if builder is None:
        raise ValueError(f"No QueryBuilder registered for {db!r}")
    return builder
