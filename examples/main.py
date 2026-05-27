from biocurator.core.curator import Biocurator
from biocurator.config.schema import (
    JobConfig,
    SearchConfig,
    FilterConfig,
    ExportConfig,
)


def main() -> None:
    job = JobConfig(
        name="my-job",
        search=SearchConfig(
            databases=["ncbi"],
            organism="SARS-CoV-2",
            sequence_type="nucleotide",
            keywords=["complete genome"],
            max_results=10,
        ),
        filter=FilterConfig(min_length=29000, quality_threshold=0.8),
        export=ExportConfig(outdir="results", formats=["fasta", "csv"], prefix="sars"),
    )

    curator = Biocurator(email="your@email.com")
    output_files = curator.run_job(job)

    print(output_files)
    # {"fasta": PosixPath("results/sars_sequences.fasta"), "csv": PosixPath("results/sars_metadata.csv")}


if __name__ == "__main__":
    main()
