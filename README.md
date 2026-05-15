# ASFV Genome Extraction Pipeline

A comprehensive bioinformatics pipeline for extracting and analyzing African Swine Fever Virus (ASFV) genomes.

## Overview

This pipeline automates the process of:

1. Searching NCBI databases for ASFV genome sequences
2. Filtering for sequences from a specified geographic location
3. Downloading and organizing the sequences
4. Performing basic genomic analysis
5. Generating summary reports and visualizations

## Features

- **Automated NCBI Search**: searches multiple databases with customizable items
- **Location-based Filtering**: specifically target sequences collected from a geographic target
- **Quality Control**: filter sequences based on length and quality criteria
- **Comprehensive Analysis**: provide sequence statistics, composition analysis, and conservation screening
- **Rich Visualizations**: generates publication-ready plots and graphs
- **Flexible Configuration**: easily customizable search parameters
- **Detailed Logging**: comprehensive logs for troubleshooting and reproducibility

## Requirements

### Python Dependencies

```bash
pip install -r requirements.txt
```

Required packages:

- biopython (>=1.79)
- requests (>=2.28.0)
- pandas (>=1.5.0)
- numpy (>=1.21.0)
- matplotlib (>=3.5.0)
- seaborn (>=0.11.0)

### Optional Tools

- **entrez-direct**: For enhanced NCBI database access

  ```bash
  # Via conda
  conda install -c bioconda entrez-direct

  # Or via apt (Ubuntu/Debian)
  sudo apt-get install ncbi-entrez-direct
  ```

## Quick Start

### 1. Basic Usage

```bash
# Make the script executable
chmod +x run_asfv_pipeline.sh

# Run with automatic dependency installation
./run_asfv_pipeline.sh --email your.email@university.edu --install-deps

# Or run without dependency installation
./run_asfv_pipeline.sh --email your.email@university.edu
```

### 2. Python Direct Usage

```bash
# Run the main pipeline
python3 asfv_philippines_pipeline.py --email your.email@university.edu

# Run analysis on downloaded genomes
python3 analyze_genomes.py --input-dir asfv_philippines_genomes
```

## Detailed Usage

### Main Pipeline Script

```bash
python3 asfv_philippines_pipeline.py [OPTIONS]

Required:
  --email EMAIL        Your email address for NCBI Entrez (required by NCBI)

Optional:
  --output-dir DIR     Output directory (default: asfv_philippines_genomes)
```

### Analysis Script

```bash
python3 analyze_genomes.py [OPTIONS]

Optional:
  --input-dir DIR      Directory containing downloaded genomes
  --output-dir DIR     Output directory for analysis results
```

### Shell Wrapper

```bash
./run_asfv_pipeline.sh [OPTIONS]

Required:
  --email EMAIL        Your email address for NCBI Entrez

Optional:
  --output-dir DIR     Output directory
  --install-deps       Install Python dependencies automatically
  --help              Show help message
```

## Output Files

### Main Pipeline Outputs

1. **asfv_philippines_genomes.fasta**
   - FASTA file containing all downloaded ASFV genome sequences
   - Sequences have descriptive headers with accession and metadata
2. **asfv_philippines_metadata.csv**
   - Detailed metadata for each sequence including:
     - Accession numbers
     - Sequence lengths
     - Organism information
     - Publication dates
     - Download status
3. **extraction_summary.txt**
   - Summary report with:
     - Total sequences downloaded
     - Length statistics
     - List of all sequences
     - File descriptions
4. **asfv_pipeline.log**
   - Detailed execution log for troubleshooting

### Analysis Outputs

1. **sequence_statistics.csv**
   - Detailed statistics for each genome:
     - Length, GC content
     - Nucleotide composition
     - AT/GC skew values
2. **genome_analysis_plots.png**
   - Comprehensive visualization including:
     - Length distribution
     - GC content analysis
     - Nucleotide composition
     - Comparative plots
3. **conserved_regions.csv**
   - Potentially conserved regions across genomes
   - Useful for identifying important functional regions
4. **analysis_summary.txt**
   - Summary of analysis results and recommendations

## Configuration

Edit `pipeline_config.ini` to customize:

- **Search Terms**: Add specific ASFV strain names or Philippines locations
- **Sequence Filters**: Adjust length ranges and quality thresholds
- **Output Options**: Customize file naming and header information
- **Analysis Parameters**: Modify conservation analysis settings
  Example configuration modifications:

```ini
[search_parameters]
# Add specific strain names
asfv_terms = African swine fever virus, ASFV, ASFV-G-I, Georgia 2007/1

# Add more specific Philippines locations
philippines_terms = Philippines, Luzon, NCR, CALABARZON, Central Luzon

[filtering]
# Exclude unwanted sequence types
exclude_terms = synthetic, artificial, vector, plasmid
```

## Workflow Steps

### Step 1: Database Search

- Constructs optimized search queries for NCBI
- Searches nucleotide database for ASFV sequences
- Filters by sequence length and relevance

### Step 2: Location Filtering

- Examines sequence titles and metadata
- Identifies sequences from Philippines samples
- Validates ASFV classification

### Step 3: Sequence Download

- Downloads FASTA sequences in batches
- Implements rate limiting to respect NCBI policies
- Handles errors and retries failed downloads

### Step 4: Data Organization

- Creates structured output directory
- Generates comprehensive metadata
- Produces summary statistics

### Step 5: Analysis (Optional)

- Calculates sequence composition statistics
- Identifies potential conserved regions
- Creates publication-ready visualizations

## Troubleshooting

### Common Issues

1. **No sequences found**
   - Check internet connection
   - Verify email format
   - Try broadening search terms in config file
2. **Download failures**
   - NCBI servers may be busy - retry later
   - Check firewall settings
   - Verify NCBI access from your network
3. **Permission errors**
   - Ensure write permissions in output directory
   - Check disk space availability
4. **Missing dependencies**
   - Run with `--install-deps` flag
   - Manually install packages: `pip install -r requirements.txt`

### Log Analysis

Check the log files for detailed error information:

```bash
# View the main pipeline log
cat asfv_pipeline.log

# View recent log entries
tail -f asfv_pipeline.log
```

## Advanced Usage

### Custom Search Queries

For more specific searches, you can modify the search terms directly:

```python
# In asfv_philippines_pipeline.py, modify the search terms
self.asfv_terms = [
    "African swine fever virus",
    "ASFV",
    "Your specific strain name"
]

self.philippines_terms = [
    "Philippines",
    "Your specific region"
]
```

### Batch Processing

To process multiple searches or compare different parameters:

```bash
# Create multiple configuration files
cp pipeline_config.ini config_luzon.ini
cp pipeline_config.ini config_mindanao.ini

# Run separate extractions
python3 asfv_philippines_pipeline.py --email your@email.com --output-dir luzon_genomes
python3 asfv_philippines_pipeline.py --email your@email.com --output-dir mindanao_genomes
```

### Integration with Other Tools

The pipeline outputs are compatible with standard bioinformatics tools:

```bash
# Multiple sequence alignment with MAFFT
mafft --auto asfv_philippines_genomes.fasta > aligned_genomes.fasta

# Phylogenetic analysis with FastTree
FastTree -nt -gtr aligned_genomes.fasta > phylogenetic_tree.newick

# Genome annotation with Prokka
prokka --outdir annotation_results --genus Asfivirus asfv_philippines_genomes.fasta
```

## Citations and Data Usage

### Citing This Pipeline

If you use this pipeline in your research, please cite:

```
ASFV Philippines Genome Extraction Pipeline
Available at: [Your repository URL]
Accessed: [Date]
```

### Data Sources

- **NCBI GenBank**: https://www.ncbi.nlm.nih.gov/genbank/
- **Nucleotide Database**: https://www.ncbi.nlm.nih.gov/nucleotide/

### NCBI Usage Guidelines

- Always provide a valid email address for NCBI Entrez
- Respect rate limits (implemented in the pipeline)
- Follow NCBI's terms of service for data usage

## Contributing

To contribute to this pipeline:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Bug Reports

Please report bugs with:

- Pipeline version
- Error messages
- Log file contents
- System information

## License

This pipeline is released under the MIT License. See LICENSE file for details.

## Support

For support and questions:

- Check the troubleshooting section above
- Review the log files for error details
- Open an issue in the repository

## Changelog

### Version 1.0.0

- Initial release
- NCBI search and download functionality
- Basic genome analysis
- Visualization generation
- Configuration system
