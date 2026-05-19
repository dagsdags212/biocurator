# Examples

Ready-to-use config examples for common bioinformatics tasks. Copy any of these into a `config.yaml`, update the email, and run with `biocurator run config.yaml`.

---

## Viral genomics

### Complete SARS-CoV-2 genomes from 2024

```yaml
email: researcher@example.com

jobs:
  sars-cov2-2024:
    search:
      databases: [ncbi]
      organism: "SARS-CoV-2"
      sequence_type: nucleotide
      keywords: ["complete genome"]
      max_results: 500
      exclude_terms: [synthetic, artificial, recombinant]
      date_range:
        start: "2024/01/01"
        end: "2024/12/31"
    filter:
      min_length: 29000
      quality_threshold: 0.9
    export:
      outdir: results/sars_2024
      formats: [fasta, csv]
      prefix: sars_cov2_2024
```

```bash
biocurator run config.yaml
```

---

### African swine fever virus (ASFV) genomes

```yaml
email: researcher@example.com

jobs:
  asfv-genomes:
    search:
      databases: [ncbi]
      organism: "African swine fever virus"
      sequence_type: nucleotide
      keywords: ["complete genome"]
      max_results: 25
      exclude_terms: [recombinant]
      date_range:
        start: "2020/01/01"
        end: "2026/05/15"
    filter: {}
    export:
      outdir: results/asfv
      formats: [fasta, csv, json]
      prefix: asfv
```

---

### Influenza A hemagglutinin segments

```yaml
email: researcher@example.com

jobs:
  influenza-ha:
    search:
      databases: [ncbi]
      organism: "Influenza A virus"
      sequence_type: nucleotide
      keywords: ["hemagglutinin", "segment 4"]
      max_results: 300
      exclude_terms: [partial, synthetic]
    filter:
      min_length: 1650
      max_length: 1800
      quality_threshold: 0.95
    export:
      outdir: results/influenza/ha
      formats: [fasta, csv]
      prefix: flu_a_ha
```

---

## Antimicrobial resistance

### Beta-lactamase genes

```yaml
email: researcher@example.com

jobs:
  beta-lactamase:
    search:
      databases: [ncbi]
      sequence_type: nucleotide
      keywords: ["beta-lactamase", "bla gene"]
      max_results: 300
      exclude_terms: [partial, predicted, hypothetical]
    filter:
      min_length: 500
      max_length: 3000
    export:
      outdir: results/amr/bla
      formats: [fasta, csv, json]
      prefix: bla_genes
```

---

### Efflux pump proteins from *M. tuberculosis*

```yaml
email: researcher@example.com

jobs:
  mtb-efflux:
    search:
      databases: [ncbi, uniprot]
      organism: "Mycobacterium tuberculosis"
      sequence_type: protein
      keywords: ["efflux pump", "drug resistance"]
      max_results: 200
      exclude_terms: [hypothetical, putative]
    filter:
      min_length: 200
      max_length: 1200
      quality_threshold: 0.95
    export:
      outdir: results/mtb/efflux
      formats: [fasta, csv]
      prefix: mtb_efflux
```

---

## Protein families

### Cytochrome P450 enzymes (multi-database)

Query both NCBI and UniProt in a single job:

```yaml
email: researcher@example.com

jobs:
  cytochrome-p450:
    search:
      databases: [ncbi, uniprot]
      sequence_type: protein
      keywords: ["cytochrome P450", "CYP"]
      max_results: 200
    filter:
      min_length: 300
      quality_threshold: 0.8
    export:
      outdir: results/cyp450
      formats: [fasta, csv]
      prefix: cyp450
```

---

### Human kinases from UniProt

```yaml
email: researcher@example.com

jobs:
  human-kinases:
    search:
      databases: [uniprot]
      organism: "Homo sapiens"
      sequence_type: protein
      keywords: ["kinase"]
      max_results: 500
    filter:
      min_length: 250
      quality_threshold: 0.99
    export:
      outdir: results/kinases
      formats: [fasta, csv]
      prefix: human_kinases
```

---

## SARS-CoV-2 structural proteins

Collect multiple protein types in one config by defining separate jobs:

```yaml
email: researcher@example.com

jobs:
  spike-proteins:
    search:
      databases: [uniprot]
      organism: "SARS-CoV-2"
      sequence_type: protein
      keywords: ["spike glycoprotein"]
      max_results: 100
    filter:
      min_length: 1200
    export:
      outdir: results/sars/spike
      formats: [fasta]
      prefix: spike

  nucleocapsid-proteins:
    search:
      databases: [uniprot]
      organism: "SARS-CoV-2"
      sequence_type: protein
      keywords: ["nucleocapsid protein"]
      max_results: 100
    filter:
      min_length: 400
    export:
      outdir: results/sars/ncap
      formats: [fasta]
      prefix: ncap

  envelope-proteins:
    search:
      databases: [uniprot]
      organism: "SARS-CoV-2"
      sequence_type: protein
      keywords: ["envelope protein"]
      max_results: 100
    filter:
      min_length: 75
    export:
      outdir: results/sars/envelope
      formats: [fasta]
      prefix: envelope
```

Run all three at once:

```bash
biocurator run config.yaml
```

Run only the spike job:

```bash
biocurator run config.yaml --jobs spike-proteins
```

Run spike and nucleocapsid, skip envelope:

```bash
biocurator run config.yaml --jobs spike-proteins,nucleocapsid-proteins
```

---

## Geographic and taxonomic filtering

### Dengue sequences from Southeast Asia

```yaml
email: researcher@example.com

jobs:
  dengue-sea:
    search:
      databases: [ncbi]
      organism: "Dengue virus"
      sequence_type: nucleotide
      keywords: ["complete genome"]
      max_results: 200
      location: "Southeast Asia"
    filter:
      min_length: 10000
      quality_threshold: 0.95
    export:
      outdir: results/dengue/sea
      formats: [fasta, csv]
      prefix: dengue_sea
```

---

### All sequences under a taxonomy ID

Use a taxonomy ID to capture an entire clade:

```yaml
email: researcher@example.com

jobs:
  betacoronavirus:
    search:
      databases: [ncbi]
      sequence_type: nucleotide
      keywords: ["complete genome"]
      max_results: 300
      taxonomy_filter: "694002"    # Betacoronavirus taxonomy ID
    filter:
      min_length: 26000
    export:
      outdir: results/betacov
      formats: [fasta, csv]
      prefix: betacov
```

---

## Workflow tip: dry-run first

Always preview before a large download:

```bash
biocurator run config.yaml --dry-run
```

```
Dry run — 3 job(s) would execute:
  • spike-proteins        databases=['uniprot']
  • nucleocapsid-proteins databases=['uniprot']
  • envelope-proteins     databases=['uniprot']
```

---

Next: [[Python API]]
