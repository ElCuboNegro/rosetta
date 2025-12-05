# Rosetta - Spanish-Hebrew Dictionary Generator

A production-ready Kedro pipeline for generating polysemic Spanish-Hebrew dictionaries from Wiktionary and Tatoeba data.

## Quick Start

### 1. Install Dependencies

```bash
pip install -e .
```

### 2. Download Wiktionary Dumps (Optional)

For real data processing, download the latest Wiktionary dumps:

```bash
# Spanish Wiktionary
wget https://dumps.wikimedia.org/eswiktionary/latest/eswiktionary-latest-pages-articles.xml.bz2 -O data/01_raw/eswiktionary-latest-pages-articles.xml.bz2

# Hebrew Wiktionary  
wget https://dumps.wikimedia.org/hewiktionary/latest/hewiktionary-latest-pages-articles.xml.bz2 -O data/01_raw/hewiktionary-latest-pages-articles.xml.bz2
```

**Note**: The pipeline works with mock data by default. Real dumps are 100MB-1GB compressed.

### 3. Download Tatoeba Sentences (Optional)

```bash
wget https://downloads.tatoeba.org/exports/sentences.tar.bz2
tar -xjf sentences.tar.bz2
mv sentences.csv data/01_raw/tatoeba-sentences.csv
```

### 4. Update Catalog (if using real data)

Edit `conf/base/catalog.yml` to point to the real dump files:

```yaml
wiktionary_es_dump:
  type: text.TextDataset
  filepath: data/01_raw/eswiktionary-latest-pages-articles.xml.bz2

wiktionary_he_dump:
  type: text.TextDataset
  filepath: data/01_raw/hewiktionary-latest-pages-articles.xml.bz2
```

### 5. Run the Pipeline

```bash
python -m kedro run
```

## Pipeline Architecture

The dictionary generation is split into three modular pipelines:

### 1. **data_processing** (Harvester)
Extracts and parses raw linguistic data:
- `parse_spanish_wiktionary` - Parses Spanish entries with wiktextract
- `parse_hebrew_wiktionary` - Parses Hebrew entries with wiktextract  
- `process_tatoeba` - Processes bilingual sentence pairs

### 2. **data_science** (Aligner)
Links languages and structures polysemic senses:
- `align_languages` - Matches Spanish↔Hebrew using translation links + rapidfuzz
- `enrich_entries` - Adds example sentences from Tatoeba
- `structure_senses` - Groups by word, creates sense_id for each meaning

### 3. **reporting** (Architect)
Final JSON formatting with metadata:
- `format_final_json` - Wraps data with version, source, and date

## Output Format

Generates JSON matching this exact schema:

```json
{
  "metadata": {
    "language_direction": "es-he | he-es",
    "version": "1.0",
    "source": "custom (Wiktionary + Tatoeba)",
    "generated_at": "2025-12-03"
  },
  "entries": [
    {
      "id": "es: banco",
      "entry": {
        "word": "banco",
        "ipa": "ˈbaŋ.ko",
        "language": "es",
        "etymology": null,
        "senses": [
          {
            "sense_id": 1,
            "definition": "Asiento alargado para varias personas.",
            "ipa_hebrew": "saˈf-sal",
            "hebrew": "ספסל",
            "pos": "noun",
            "examples": [
              {
                "es": "Nos sentamos en el banco del parque.",
                "he": "ישבנו על הספסל בפארק."
              }
            ]
          }
        ]
      }
    }
  ]
}
```

## Development

### Run Specific Pipelines

```bash
# Run only harvester
python -m kedro run --pipeline=data_processing

# Run only aligner
python -m kedro run --pipeline=data_science

# Run only architect
python -m kedro run --pipeline=reporting
```

### Parallel Execution

For faster processing of large dumps:

```bash
python -m kedro run --runner=ParallelRunner
```

### Kedro Viz

Visualize the pipeline:

```bash
python -m kedro viz
```

## Project Structure

```
rosetta/
├── conf/
│   └── base/
│       └── catalog.yml          # Data sources configuration
├── data/
│   ├── 01_raw/                  # Input: Wiktionary dumps, Tatoeba
│   ├── 02_intermediate/         # Parsed entries
│   ├── 03_primary/              # Aligned & enriched data
│   └── 08_reporting/            # Final dictionary JSON
└── src/rosetta_dict/
    └── pipelines/
        ├── data_processing/     # Harvester nodes
        ├── data_science/        # Aligner nodes
        └── reporting/           # Architect nodes
```

## Dependencies

Core libraries:
- `kedro~=1.0.0` - Pipeline orchestration
- `wiktextract>=1.99.0` - Wiktionary parsing
- `rapidfuzz>=3.0.0` - Fuzzy string matching
- `pandas>=2.0.0` - Data manipulation
- `pyarrow>=15.0.0` - Parquet support

## License

MIT
