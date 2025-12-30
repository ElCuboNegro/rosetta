# Rosetta Dictionary

A Spanish-Hebrew bilingual dictionary project built with Kedro, leveraging Wiktionary data, Project Gutenberg texts, and the Ben Yehuda corpus for cross-lingual learning and sense induction.

## Overview

This project creates a rich bilingual dictionary by:
- Extracting entries from Spanish and Hebrew Wiktionary
- Aligning parallel texts from Project Gutenberg and Ben Yehuda corpus
- Performing word sense induction using contextual embeddings
- Providing interactive tools for review and refinement

## Tech Stack

- **Pipeline Framework**: Kedro
- **Database**: PostgreSQL
- **NLP**: spaCy, sentence-transformers (BERT)
- **Language**: Python 3.13+
- **Data Sources**: Wiktionary (kaikki.org), Project Gutenberg, Ben Yehuda Archive

## Quick Start

### Prerequisites

1. **PostgreSQL** (Docker recommended):
   ```bash
   docker-compose up -d
   ```

2. **Python Environment**:
   ```bash
   conda create -n rosetta python=3.13
   conda activate rosetta
   pip install -r requirements.txt
   ```

### Running the Pipeline

```bash
# Run full pipeline
kedro run

# Run specific pipeline
kedro run --pipeline=data_acquisition
kedro run --pipeline=catalog_alignment
kedro run --pipeline=book_alignment
kedro run --pipeline=sense_induction
```

## Project Structure

```
rosetta/
├── conf/                       # Kedro configuration
│   ├── base/
│   │   ├── catalog.yml        # Data catalog (PostgreSQL datasets)
│   │   └── parameters.yml     # Pipeline parameters
│   └── local/
│       └── credentials.yml    # Database credentials (not in git)
├── data/                      # Data directory
│   ├── 01_raw/               # Raw data sources
│   │   ├── ben_yehuda_dump/  # Hebrew corpus (~25K texts)
│   │   └── gutenberg/        # Project Gutenberg downloads
│   ├── 02_intermediate/      # Processed data
│   ├── 03_primary/           # Aligned dictionaries
│   └── 04_feature/           # Sense clusters
├── src/rosetta_dict/
│   └── pipelines/            # Kedro pipelines
│       ├── data_acquisition/  # Download & parse Wiktionary/Gutenberg
│       ├── catalog_alignment/ # Match book catalogs (BERT)
│       ├── book_alignment/    # Align sentence pairs
│       ├── sense_induction/   # Cluster word senses
│       └── ...
├── scripts/                   # Utility scripts
│   ├── cluster_review_ui.py  # Interactive sense review
│   └── ...
├── migrations/                # PostgreSQL schema migrations
└── .llm-docs/                 # AI-generated documentation (see .llm-docs/README.md)
```

## Key Features

### 1. Multilingual Catalog Alignment
- Matches Ben Yehuda (Hebrew) books with Gutenberg (Spanish/English) using BERT embeddings
- Wikidata enrichment for author matching
- **268 validated alignments** with false positive prevention

### 2. Book-Level Sentence Alignment
- LaBSE embeddings for cross-lingual similarity
- Hebrew sentence segmentation with line-joining heuristics
- Validation using BookPairValidator

### 3. Word Sense Induction
- Clusters word usage contexts using HDBSCAN/KMeans
- Ensemble embeddings (word + context + sentence)
- Quality metrics and manual review UI

### 4. PostgreSQL Integration
- All data persisted in PostgreSQL
- ~1.7M rows across 24 tables
- Full migration from Parquet completed

## Documentation

For detailed guides and development notes, see [`.llm-docs/README.md`](.llm-docs/README.md):
- PostgreSQL setup and migration
- Pipeline parameters and configuration
- Feature guides (book validation, sense clustering, etc.)
- Development improvements and fixes

## Database

### Tables (Selected)

| Table | Rows | Description |
|-------|------|-------------|
| `raw_spanish_entries` | 787,115 | Spanish Wiktionary entries |
| `benyehuda_catalog_raw` | 24,973 | Ben Yehuda book metadata |
| `raw_hebrew_entries` | 15,116 | Hebrew Wiktionary entries |
| `sense_clusters` | 3,897 | Induced word senses |
| `gutenberg_catalog` | 2,915 | Gutenberg book metadata |
| `aligned_catalogs` | 268 | Book pairs (Hebrew ↔ Spanish/English) |

### Credentials

Create `conf/local/credentials.yml`:
```yaml
postgres_warehouse:
  con: postgresql://postgres:your_password@localhost:5432/rosetta
```

## Development

### Adding a Pipeline

```python
# src/rosetta_dict/pipelines/my_pipeline/nodes.py
def my_node(input_data):
    # Process data
    return output_data

# src/rosetta_dict/pipelines/my_pipeline/pipeline.py
from kedro.pipeline import Pipeline, node
from .nodes import my_node

def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline([
        node(func=my_node, inputs="input_dataset", outputs="output_dataset")
    ])
```

### Running Tests

```bash
pytest tests/
```

## Contributing

This is a research/learning project. Feel free to explore and adapt for your own use.

## Data Sources

- **Wiktionary**: Via [kaikki.org](https://kaikki.org) pre-processed dumps
- **Project Gutenberg**: Public domain books
- **Ben Yehuda Archive**: Hebrew literature corpus

## License

See project-specific licensing for data sources. Code portions may be used according to project license (if specified).

---

**Last Updated**: 2025-12-30
**Pipeline Status**: ✅ PostgreSQL migration complete, catalog alignment improved
