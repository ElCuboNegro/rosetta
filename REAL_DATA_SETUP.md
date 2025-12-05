# Setting Up Real Wiktionary Data

## Current Status ✅

The pipeline is configured for **FAIL-FAST mode** and is working correctly:
- ✅ No mock data fallbacks
- ✅ Fails immediately with invalid/missing data
- ✅ All raw data managed by Kedro parameters

## Why the Pipeline Currently Fails

The sample XML files in `data/01_raw/` are minimal placeholders that don't have proper MediaWiki XML structure. The pipeline correctly **fails immediately** when it encounters invalid data.

**This is the desired behavior!** You requested fail-fast mode with no mock data.

## How to Use Real Wiktionary Data

### Option 1: Download Real Dumps (Recommended for Production)

#### Step 1: Download Wiktionary Dumps

```bash
cd data/01_raw

# Spanish Wiktionary (~350MB compressed, ~2GB uncompressed)
curl -O https://dumps.wikimedia.org/eswiktionary/latest/eswiktionary-latest-pages-articles.xml.bz2

# Hebrew Wiktionary (~100MB compressed, ~500MB uncompressed)
curl -O https://dumps.wikimedia.org/hewiktionary/latest/hewiktionary-latest-pages-articles.xml.bz2
```

Or using wget:
```bash
wget https://dumps.wikimedia.org/eswiktionary/latest/eswiktionary-latest-pages-articles.xml.bz2
wget https://dumps.wikimedia.org/hewiktionary/latest/hewiktionary-latest-pages-articles.xml.bz2
```

#### Step 2: Update Configuration

Edit `conf/base/parameters.yml`:

```yaml
# Pipeline Parameters

# Wiktionary dump file paths  
wiktionary:
  es_dump_path: "data/01_raw/eswiktionary-latest-pages-articles.xml.bz2"
  he_dump_path: "data/01_raw/hewiktionary-latest-pages-articles.xml.bz2"
```

**Note**: wiktextract can read `.bz2` compressed files directly - no need to decompress!

#### Step 3: Run Pipeline

```bash
python -m kedro run
```

**Expected Duration**: 10-30 minutes
**Expected Output**: 30,000-40,000 Spanish words with Hebrew translations

### Option 2: Keep Sample Files for Testing (Only for Dev)

If you want to test the pipeline structure without downloading large dumps, you can create minimal valid XML files. However, these won't produce useful dictionary data.

#### Create Valid Sample Files

Replace `data/01_raw/eswiktionary-sample.txt`:
```xml
<mediawiki xmlns="http://www.mediawiki.org/xml/export-0.10/" version="0.10">
  <page>
    <title>Test</title>
    <ns>0</ns>
    <id>1</id>
    <revision>
      <id>1</id>
      <timestamp>2024-01-01T00:00:00Z</timestamp>
      <contributor><username>Test</username></contributor>
      <model>wikitext</model>
      <format>text/x-wiki</format>
      <text xml:space="preserve">Test content</text>
    </revision>
  </page>
</mediawiki>
```

Replace `data/01_raw/hewiktionary-sample.txt` with the same structure.

**Important**: These minimal files will allow the pipeline to run but won't extract any useful dictionary data. They're only for structural testing.

## Configuration Files Reference

### `conf/base/parameters.yml`
Defines Wiktionary dump file paths:
```yaml
wiktionary:
  es_dump_path: "data/01_raw/eswiktionary-latest-pages-articles.xml.bz2"
  he_dump_path: "data/01_raw/hewiktionary-latest-pages-articles.xml.bz2"
```

### `conf/base/catalog.yml`
Defines Tatoeba input and output datasets:
```yaml
tatoeba_sentences:
  type: pandas.CSVDataset
  filepath: data/01_raw/tatoeba-sample.csv

raw_spanish_entries:
  type: pandas.ParquetDataset
  filepath: data/02_intermediate/spanish_entries.parquet
  
# ... other datasets
```

## Verifying Your Setup

### Check File Sizes
Real Wiktionary dumps should be:
- Spanish: ~350MB (.bz2) or ~2GB (uncompressed)
- Hebrew: ~100MB (.bz2) or ~500MB (uncompressed)

If files are only a few KB, they're sample files that won't work.

### Check Pipeline Parameters
```bash
python -m kedro catalog list --pipeline=data_processing
```

Should show `params:wiktionary.es_dump_path` and `params:wiktionary.he_dump_path` as inputs.

## Troubleshooting

### AssertionError in wikitextprocessor
**Cause**: Invalid XML structure (missing `<model>` tag or malformed MediaWiki XML)  
**Solution**: Download real Wiktionary dumps or create properly formatted test XML

### FileNotFoundError
**Cause**: Dump file path in `parameters.yml` doesn't exist  
**Solution**: Verify files exist in `data/01_raw/` and paths in `parameters.yml` are correct

### ImportError: wiktextract
**Cause**: wiktextract not installed  
**Solution**: `pip install wiktextract>=1.99.0`

## Production Deployment

For production use:
1. ✅ Download real Wiktionary dumps
2. ✅ Update `parameters.yml` with correct paths  
3. ✅ Consider using `--runner=ParallelRunner` for faster processing
4. ✅ Monitor output in `data/08_reporting/dictionary.json`
5. ✅ Set up periodic re-runs (Wiktionary updates monthly)

## Next Steps

After getting real data:
1. Run the full pipeline: `python -m kedro run`
2. Inspect intermediate outputs in `data/02_intermediate/`
3. Review final JSON in `data/08_reporting/dictionary.json`
4. Validate output structure matches your requirements
5. Consider adding custom post-processing nodes if needed
