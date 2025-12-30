"""
Smart migration script that converts array/list columns to JSON for JSONB fields.

Usage:
    python scripts/migrate_with_json_conversion.py          # Normal mode
    python scripts/migrate_with_json_conversion.py --verbose # Show full errors
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from tqdm import tqdm

# Global verbose flag
VERBOSE = False

# Setup logging with simpler format
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",  # Removed timestamp for cleaner output
)
logger = logging.getLogger(__name__)

# Database connection
CONNECTION_STRING = "postgresql://postgres:rosetta_password@localhost:5432/rosetta"

# Tables with their file paths and columns that need JSON conversion
TABLES_TO_MIGRATE = {
    "raw_spanish_entries_unfiltered": {
        "file": "data/02_intermediate/raw_spanish_entries_unfiltered.parquet",
        "json_columns": [
            "definitions",
            "examples",
            "translations_en",
            "translations_fr",
            "translations_de",
            "translations_he",
        ],
    },
    "raw_hebrew_entries_unfiltered": {
        "file": "data/02_intermediate/raw_hebrew_entries_unfiltered.parquet",
        "json_columns": [
            "definitions",
            "translations_en",
            "translations_fr",
            "translations_de",
            "translations_es",
        ],
    },
    "raw_spanish_entries_filtered": {
        "file": "data/02_intermediate/raw_spanish_entries_filtered.parquet",
        "json_columns": [
            "definitions",
            "examples",
            "translations_en",
            "translations_fr",
            "translations_de",
            "translations_he",
        ],
    },
    "raw_hebrew_entries_filtered": {
        "file": "data/02_intermediate/raw_hebrew_entries_filtered.parquet",
        "json_columns": [
            "definitions",
            "translations_en",
            "translations_fr",
            "translations_de",
            "translations_es",
        ],
    },
    "raw_spanish_entries": {
        "file": "data/02_intermediate/raw_spanish_entries.parquet",
        "json_columns": [
            "definitions",
            "examples",
            "translations_en",
            "translations_fr",
            "translations_de",
            "translations_he",
        ],
    },
    "raw_hebrew_entries": {
        "file": "data/02_intermediate/raw_hebrew_entries.parquet",
        "json_columns": [
            "definitions",
            "translations_en",
            "translations_fr",
            "translations_de",
            "translations_es",
        ],
    },
}


def convert_numpy_to_list(obj):
    """Recursively convert numpy arrays to lists."""
    if isinstance(obj, np.ndarray):
        return [convert_numpy_to_list(item) for item in obj]
    elif isinstance(obj, list):
        return [convert_numpy_to_list(item) for item in obj]
    elif isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    else:
        return obj


def convert_to_json(value):
    """Convert Python objects to JSON strings for JSONB columns."""
    # Check for numpy arrays and lists first (before pd.isna check)
    if isinstance(value, (list, np.ndarray)):
        # Recursively convert all nested numpy arrays to lists
        value = convert_numpy_to_list(value)
        return json.dumps(value, ensure_ascii=False)

    # Now safe to check pd.isna for scalar values
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "[]"

    if isinstance(value, str):
        # Already a string, return as-is
        return value

    # For other types, try to convert to JSON
    try:
        return json.dumps(value, ensure_ascii=False)
    except:
        return "[]"


def migrate_table(table_name, file_path, json_columns):
    """Migrate a table with JSON conversion."""
    print(f"\n{'=' * 60}")
    print(f"Migrating: {table_name}")
    print(f"{'=' * 60}")

    # Check if file exists
    path = Path(file_path)
    if not path.exists():
        print(f"⚠️  SKIPPED - File not found: {file_path}")
        return False

    # Load data
    try:
        df = pd.read_parquet(file_path)
        print(f"✓ Loaded {len(df):,} rows")
    except Exception as e:
        print(f"❌ ERROR loading file: {str(e)[:100]}")  # Truncate error message
        return False

    # Convert JSON columns
    print(f"Converting {len(json_columns)} JSON columns...")
    for col in json_columns:
        if col in df.columns:
            df[col] = df[col].apply(convert_to_json)

    # Migrate to PostgreSQL
    try:
        engine = create_engine(CONNECTION_STRING)
        chunk_size = 5000

        with tqdm(total=len(df), desc=f"Writing to DB", ncols=80) as pbar:
            for i in range(0, len(df), chunk_size):
                chunk = df.iloc[i : i + chunk_size]
                chunk.to_sql(table_name, engine, if_exists="append", index=False, method="multi")
                pbar.update(len(chunk))

        print(f"✅ SUCCESS - Migrated {len(df):,} rows")
        return True

    except Exception as e:
        import traceback
        from datetime import datetime

        error_msg = str(e)
        tb_full = traceback.format_exc()

        print(f"\n❌ FAILED - Migration error occurred")
        print("=" * 60)

        # Save full error to file if it's very long
        error_lines_count = len(error_msg.split("\n"))
        if error_lines_count > 100 and not VERBOSE:
            error_file = (
                f"migration_error_{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )
            try:
                with open(error_file, "w", encoding="utf-8") as f:
                    f.write(f"Migration Error for: {table_name}\n")
                    f.write(f"Time: {datetime.now()}\n")
                    f.write("=" * 60 + "\n\n")
                    f.write("FULL ERROR MESSAGE:\n")
                    f.write("=" * 60 + "\n")
                    f.write(error_msg)
                    f.write("\n\n" + "=" * 60 + "\n")
                    f.write("FULL TRACEBACK:\n")
                    f.write("=" * 60 + "\n")
                    f.write(tb_full)
                print(f"📄 Full error saved to: {error_file}")
                print("=" * 60)
            except Exception as write_error:
                print(f"⚠️  Could not save error to file: {write_error}")
                print("=" * 60)

        # Extract key information from SQLAlchemy errors
        if "sqlalchemy" in tb_full.lower() or "psycopg2" in tb_full.lower():
            print("DATABASE ERROR DETECTED")
            print("=" * 60)

            # Look for the actual SQL error in the exception
            lines = error_msg.split("\n")

            if not VERBOSE and len(lines) > 50:
                # Show critical parts only
                print("\nError Summary (first 20 lines):")
                for line in lines[:20]:
                    print(line)

                print("\n... [truncated %d lines] ...\n" % (len(lines) - 40))

                print("Error Details (last 20 lines):")
                for line in lines[-20:]:
                    print(line)
            else:
                print("\nError Message:")
                print(error_msg)

            # Extract SQL statement if present
            if "INSERT INTO" in error_msg or "CREATE TABLE" in error_msg:
                print("\n" + "=" * 60)
                print("SQL STATEMENT DETECTED - Check for:")
                print("  - Column type mismatches")
                print("  - NULL constraint violations")
                print("  - Data type conversion issues")
                print("=" * 60)

        else:
            # Non-SQL errors - show normally
            if VERBOSE or len(error_msg) <= 500:
                print("Error message:")
                print(error_msg)
            else:
                print("Error message (first 300 chars):")
                print(error_msg[:300])
                print("\n... [truncated - use --verbose] ...\n")
                print("Error message (last 300 chars):")
                print(error_msg[-300:])

        # Simplified traceback
        if VERBOSE:
            print("\n" + "=" * 60)
            print("FULL TRACEBACK:")
            print("=" * 60)
            print(tb_full)
        else:
            tb_lines = tb_full.split("\n")
            # Only show the most relevant parts
            print("\n" + "=" * 60)
            print("TRACEBACK (key lines only):")
            print("=" * 60)

            # Show lines that contain file paths (actual code locations)
            relevant_lines = [
                line
                for line in tb_lines
                if 'File "' in line or "Error" in line or "Exception" in line
            ]
            for line in relevant_lines[-15:]:  # Last 15 relevant lines
                if line.strip():
                    print(line)

        print("\n" + "=" * 60)
        if not VERBOSE:
            print("💡 Tip: Run with --verbose to see full error output")
        print("=" * 60)

        return False


def main():
    global VERBOSE

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Migrate parquet files to PostgreSQL with JSON conversion"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show full error messages and tracebacks"
    )
    args = parser.parse_args()
    VERBOSE = args.verbose

    print("\n" + "=" * 60)
    print("PostgreSQL Migration with JSON Conversion")
    if VERBOSE:
        print("Mode: VERBOSE (full errors)")
    print("=" * 60)
    print(f"Tables to migrate: {len(TABLES_TO_MIGRATE)}\n")

    results = {}

    for table_name, config in TABLES_TO_MIGRATE.items():
        success = migrate_table(table_name, config["file"], config["json_columns"])
        results[table_name] = success

    # Print summary
    print(f"\n{'=' * 60}")
    print("MIGRATION SUMMARY")
    print("=" * 60)

    success_count = sum(1 for v in results.values() if v)
    failed_count = sum(1 for v in results.values() if not v)

    print(f"✅ Success: {success_count}/{len(results)}")
    print(f"❌ Failed:  {failed_count}/{len(results)}")

    if failed_count > 0:
        print("\nFailed tables:")
        for table, success in results.items():
            if not success:
                print(f"  - {table}")
        if not VERBOSE:
            print("\nTip: Run with --verbose flag to see full error details")

    if success_count > 0:
        print("\n✓ To test your pipeline:")
        print("  python -m kedro run --pipeline sense_induction")

    print("=" * 60 + "\n")

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
