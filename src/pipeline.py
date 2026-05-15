from datetime import datetime
from pathlib import Path
from typing import Union, Any
import time
from Bio import Entrez
from Bio import SeqIO
import pandas as pd
from ._logger import logger


class AsfvGenomeExtractor:
    """Extract ASFV genomes that match specified criteria"""

    def __init__(
        self,
        search_terms: list[str],
        email: Union[str, None] = None,
        outdir: Union[str, Path] = Path("data"),
    ) -> None:
        if len(search_terms) == 0:
            # TODO: Replace with a custome exception
            raise Exception("Must provide at least one search term")
        self.search_terms = search_terms
        self.email = email
        self.outdir = Path(outdir)
        self.outdir.mkdir(exist_ok=True)

        Entrez.email = email
        Entrez.tool = "AsfvGenomeExtractor"

        # Search terms
        self.asfv_terms = ["African swine fever virus", "ASFV", "Asfaviridae"]

        self.results = []

    def query_ncbi_nucleotide(self, retmax: int = 1000) -> list[str]:
        """
        Search the NCBI nucleotide database for ASFV genomes

        Parameters
        ----------
        retmax : int
            Number of ids to return from query results

        Returns
        -------
        list[str] - list of GenBank accession IDs
        """
        logger.info("Searching NCBI Nucleotide database...")
        asfv_query = " OR ".join([f'"{term}"' for term in self.asfv_terms])
        custom_query = " OR ".join([f'"{term}"' for term in self.search_terms])
        query = (
            f"({asfv_query}) AND ({custom_query})"
            " AND (complete_genome[Title] OR genome[Title] OR genomic[Title])"
            " AND 50000:500000[Sequence Length]"
        )

        logger.info(f"Search query: {query}")

        try:
            handle = Entrez.esearch(
                db="nucleotide", term=query, retmax=retmax, sort="relevance"
            )
            results = Entrez.read(handle)
            handle.close()

            id_list = results["IdList"]
            logger.info(f"Found {len(id_list)} potential ASFV sequences")

            return id_list
        except Exception as e:
            logger.error(f"Error searching NCBI: {e}")
            return []

    def get_sequence_details(self, id_list: list[str]) -> list[dict[str, Any]]:
        """
        Fetch detailed information for each sequence id

        Parameters
        ----------
        id_list : list[str]
            List of valid NCBI identifiers

        Returns
        -------
            List of sequence details stored as dictionaries
        """
        logger.info("Fetching sequence details...")
        seq_details = []

        # Parameterize - process in batches to avoid overwhelming NCBI
        batch_size = 20

        for i in range(0, len(id_list), batch_size):
            batch = id_list[i : i + batch_size]

            try:
                # Retrieve summary info from esummary endpoint
                handle = Entrez.esummary(db="nucleotide", id=",".join(batch))
                summaries = Entrez.read(handle)
                handle.close()

                for summary in summaries:
                    title = summary.get("Title", "").lower()
                    organism = summary.get("Organism", "").lower()
                    # Keyword search
                    is_asfv = any(
                        term.lower() in title or term.lower in organism
                        for term in self.asfv_terms
                    )

                    if is_asfv:
                        seq_data = {
                            "accession": summary.get("AccessionVersion"),
                            "gi": summary.get("Gi"),
                            "title": summary.get("Title"),
                            "organism": summary.get("Organism"),
                            "length": summary.get("Length"),
                            "create_date": summary.get("CreateDate"),
                            "update_date": summary.get("UpdateDate"),
                        }
                        seq_details.append(seq_data)

                    # Be nice to NCBI servers!
                    time.sleep(0.5)

            except Exception as e:
                logger.warning(
                    f"Error fetching sequence details for batch {i//batch_size+1}: {e}"
                )

        logger.info(f"Retrieved details for {len(seq_details)} ASFV sequence records")
        return seq_details

    def filter_sequences(self, sequences: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Filter sequences based on search terms

        Parameters
        ----------
        sequences : list[dict[str, Any]]
            List of dictionaries containing sequence information

        Returns
        -------
        List of filtered sequence details
        """
        logger.info(
            f"Filtering sequences based on search terms: {','.join(self.search_terms)}"
        )
        filtered_seqs = []
        for seq in sequences:
            title_lower = seq["title"].lower()
            is_valid = any(term.lower() in title_lower for term in self.search_terms)

            if is_valid:
                filtered_seqs.append(seq)
                logger.info(
                    f"Sequence found: {seq['accession']} - {seq['title'][:100]}..."
                )
        logger.info(f"{len(filtered_seqs)} / {len(sequences)} sequences retained")
        return filtered_seqs

    def download_sequences(self, sequences: list[dict[str, Any]]) -> None:
        """
        Download FASTA sequences and related metadata

        Parameters
        ----------
        sequences : list[dict[str, Any]]
            List if dictionaries containing sequence information

        Returns
        -------
        None
        """
        nseqs = len(sequences)
        logger.info(f"Attempting to download {nseqs} sequences...")

        fasta_fp = self.outdir / "asfv_genomes.fasta"
        metadata_fp = self.outdir / "asfv_metadata.csv"

        downloaded_sequences = []

        with open(fasta_fp, "w") as fasta_handle:
            for i, seq_info in enumerate(sequences):
                try:
                    handle = Entrez.efetch(
                        db="nucleotide",
                        id=seq_info["accession"],
                        rettype="fasta",
                        retmode="text",
                    )
                    # Parse FASTA record
                    record = SeqIO.read(handle, "fasta")
                    handle.close()

                    record.id = f"{seq_info['accession']}"
                    record.description = f"{seq_info['title']}"

                    # Write FASTA
                    SeqIO.write(record, fasta_handle, "fasta")

                    # Update sequence info
                    seq_info["downloaded"] = True
                    seq_info["sequence_length"] = len(record.seq)
                    downloaded_sequences.append(seq_info)

                    logger.info(
                        f"Downloaded {seq_info['accession']} ({len(record.seq)} bp)"
                    )

                    time.sleep(0.3)

                except Exception as e:
                    logger.warning(f"Failed to download {seq_info['accession']}: {e}")
                    seq_info["donwloaded"] = False
                    continue

        if downloaded_sequences:
            df = pd.DataFrame(downloaded_sequences)
            df.to_csv(metadata_fp, index=False)
            logger.info(
                f"Saved metadata for {len(downloaded_sequences)} sequences to {str(metadata_fp)}"
            )

        self.results = downloaded_sequences

    def generate_summary_report(self) -> None:
        """Generate a summary report of the extraction"""
        logger.info("Generating summary report...")

        report_fp = self.outdir / "summary.txt"

        with report_fp.open("w") as fh:
            fh.write("ASFV Genome Extraction Summary\n")
            fh.write("=" * 50 + "\n\n")
            fh.write(
                f"Extraction Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            fh.write(f"Total Sequences Downloaded: {len(self.results)}\n\n")

            if self.results:
                # Calculate statistics
                lengths = [seq["sequence_length"] for seq in self.results]
                avg_length = sum(lengths) / len(lengths)
                min_length = min(lengths)
                max_length = max(lengths)

                fh.write("Sequence Statistics:\n")
                fh.write(f"  Average Length: {avg_length:,.0f} bp\n")
                fh.write(f"  Minimum Length: {min_length:,.0f} bp\n")
                fh.write(f"  Maximum Length: {max_length:,.0f} bp\n\n")

                fh.write("Downloaded Sequences:\n")
                for seq in self.results:
                    fh.write(
                        f"  {seq['accession']} - {seq['sequence_length']:,} bp - {seq['title'][:800]}...\n"
                    )

            fh.write("\nFiles Generated:\n")
            fh.write(f"  - {self.outdir / 'asfv_genomes.fasta'}: FASTA sequences\n")
            fh.write(f"  - {self.outdir / 'asfv_metadata.csv'}: Sequence metadata\n")
            fh.write(f"  - {self.outdir / 'summary.txt'}: This summary\n")
            fh.write(
                f"  - {self.outdir / 'asfv_genome_curator.log'}: Detailed log file\n"
            )

        logger.info(f"Summary report saved to {report_fp}")

    def run(self, retmax: int = 10) -> None:
        """Run the complete genome extraction pipeline"""
        logger.info("Starting ASFV Genome Extraction Pipeline...")

        id_list = self.query_ncbi_nucleotide(retmax=retmax)
        if not id_list:
            logger.error("No sequences found. Exiting...")
            return

        seq_details = self.get_sequence_details(id_list)
        if not seq_details:
            logger.error("No sequence details retrieved. Exiting...")
            return

        filtered_seqs = self.filter_sequences(seq_details)
        if not filtered_seqs:
            logger.warning("No search term-specific sequences found.")
            return

        self.download_sequences(filtered_seqs)
        self.generate_summary_report()

        logger.info("Pipeline completed successfully!")
        logger.info(f"Results saved in: {self.outdir}")
