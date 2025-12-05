# Setting Up Real Wiktionary Data

This guide explains how to configure the pipeline to process actual Wiktionary dumps instead of mock data.

## Step 1: Download Wiktionary Dumps

### Spanish Wiktionary (~350MB compressed, ~3GB uncompressed)

```bash
cd data/01_raw
wget https://dumps.wikimedia.org/eswiktionary/latest/eswiktionary-latest-pages-articles.xml.bz2
```

Or download manually from: https://dumps.wikimedia.org/eswiktionary/latest/

### Hebrew Wiktionary (~100MB compressed, ~1GB uncompressed)

```bash
cd data/01_raw
wget https://dumps.wikimedia.org/hewiktionary/latest/hewiktionary-latest-pages-articles.xml.bz2
```

Or download manually from: https://dumps.wikimedia.org/hewiktionary/latest/

## Step 2: Update Data Catalog

Edit `conf/base/catalog.yml` and change the file paths:

```yaml
wiktionary_es_dump:
  type: text.TextDataset
  # Old: filepath: data/01_raw/eswiktionary-sample.txt
  filepath: data/01_raw/eswiktionary-latest-pages-articles.xml.bz2

wiktionary_he_dump:
  type: text.TextDataset
  # Old: filepath: data/01_raw/hewiktionary-sample.txt
  filepath: data/01_raw/hewiktionary-latest-pages-articles.xml.bz2
```

## Step 3: (Optional) Download Tatoeba Sentences

For real example sentences, download the full Tatoeba corpus:

```bash
cd data/01_raw
wget https://downloads.tatoeba.org/exports/sentences.tar.bz2
tar -xjf sentences.tar.bz2
mv sentences.csv tatoeba-sentences.csv
```

**Warning**: The full Tatoeba dump is ~200MB uncompressed with millions of sentences.

You may want to filter for Spanish-Hebrew pairs only:

```python
import pandas as pd

# Load full sentences
df = pd.read_csv('data/01_raw/tatoeba-sentences.csv', sep='\t', header=None,
                 names=['id', 'lang', 'text'])

# Filter for Spanish and Hebrew only
es_he = df[df['lang'].isin(['spa', 'heb'])]
es_he.to_csv('data/01_raw/tatoeba-spanish-hebrew.csv', sep='\t', index=False, header=False)
```

Then update `catalog.yml`:

```yaml
tatoeba_sentences:
  type: pandas.CSVDataset
  filepath: data/01_raw/tatoeba-spanish-hebrew.csv
  load_args:
    sep: '\t'
    header: null
    names: ['id', 'lang', 'text']
```

## Step 4: Run the Pipeline

```bash
python -m kedro run
```

**Expected processing time**:
- Mock data: ~0.2 seconds
- Real Wiktionary dumps: 10-30 minutes (depends on CPU)
- With Tatoeba: Add 5-10 minutes

## Step 5: Monitor Progress

The pipeline will log its progress:

```
[INFO] Parsing Spanish Wiktionary from data/01_raw/eswiktionary-latest-pages-articles.xml.bz2...
[INFO] Starting wiktextract parsing (this may take several minutes)...
[INFO] Parsed 45,231 Spanish entries with Hebrew translations
```

## Performance Tips

### Use Parallel Execution

```bash
python -m kedro run --runner=ParallelRunner
```

This runs the Spanish and Hebrew parsers in parallel, cutting time by ~40%.

### Incremental Processing

If you want to test with a subset first:

1. Extract a small portion of the dump:
   ```bash
   bzcat eswiktionary-latest-pages-articles.xml.bz2 | head -n 10000 > eswiktionary-sample-10k.xml
   ```

2. Update catalog to point to the sample file

3. Run the pipeline

4. Once verified, switch to the full dump

## Troubleshooting

### "wiktextract not available, using mock data"

Make sure wiktextract is installed:

```bash
pip install wiktextract>=1.99.0
```

### Out of Memory Errors

Wiktextract loads the entire dump. For very large dumps:

1. Increase system swap space
2. Use a machine with more RAM (16GB+ recommended)
3. Process dumps on a server instead of locally

### Slow Processing

- **Normal**: Spanish Wiktionary takes 15-20 minutes on a modern CPU
- **Slow** (>1 hour): Check if antivirus is scanning the dump file
- Use `--runner=ParallelRunner` to speed up

## Expected Output

With real Wiktionary data, you'll get:

- **Spanish entries**: 40,000-50,000 words with Hebrew translations
- **Hebrew entries**: 20,000-30,000 words with Spanish translations  
- **Final dictionary**: 30,000-40,000 unique Spanish words (some without he translations are filtered)

Output location: `data/08_reporting/dictionary_v1.json`
