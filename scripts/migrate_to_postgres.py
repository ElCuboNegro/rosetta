"""
Data Migration Script: Parquet/CSV → PostgreSQL
Migrates all data from parquet and CSV files to PostgreSQL warehouse.

Usage:
    python scripts/migrate_to_postgres.py --all
    python scripts/migrate_to_postgres.py --table sense_clusters
    python scripts/migrate_to_postgres.py --dry-run
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from sqlalchemy import create_engine
from tqdm import tqdm

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database connection
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'rosetta',
    'user': 'postgres',
    'password': 'rosetta_password'
}

# Connection string for SQLAlchemy
CONNECTION_STRING = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

# Mapping: dataset name → (file_path, table_name, file_type)
MIGRATION_MAP = {
    # Sense induction data
    'sense_clusters': (
        'data/04_feature/sense_clusters.parquet',
        'sense_clusters',
        'parquet'
    ),
    'aligned_book_sentences': (
        'data/02_intermediate/aligned_books.parquet',
        'aligned_book_sentences',
        'parquet'
    ),

    # Wiktionary data
    'raw_spanish_entries_unfiltered': (
        'data/02_intermediate/raw_spanish_entries_unfiltered.parquet',
        'raw_spanish_entries_unfiltered',
        'parquet'
    ),
    'raw_hebrew_entries_unfiltered': (
        'data/02_intermediate/raw_hebrew_entries_unfiltered.parquet',
        'raw_hebrew_entries_unfiltered',
        'parquet'
    ),
    'raw_spanish_entries_filtered': (
        'data/02_intermediate/raw_spanish_entries_filtered.parquet',
        'raw_spanish_entries_filtered',
        'parquet'
    ),
    'raw_hebrew_entries_filtered': (
        'data/02_intermediate/raw_hebrew_entries_filtered.parquet',
        'raw_hebrew_entries_filtered',
        'parquet'
    ),
    'raw_spanish_entries': (
        'data/02_intermediate/raw_spanish_entries.parquet',
        'raw_spanish_entries',
        'parquet'
    ),
    'raw_hebrew_entries': (
        'data/02_intermediate/raw_hebrew_entries.parquet',
        'raw_hebrew_entries',
        'parquet'
    ),
    'wiktionary_examples_tagged': (
        'data/02_intermediate/wiktionary_examples_tagged.parquet',
        'wiktionary_examples_tagged',
        'parquet'
    ),
    'tatoeba_examples_tagged': (
        'data/02_intermediate/tatoeba_examples_tagged.parquet',
        'tatoeba_examples_tagged',
        'parquet'
    ),
    'clean_examples': (
        'data/02_intermediate/clean_examples.parquet',
        'clean_examples',
        'parquet'
    ),

    # Alignment data
    'bridge_entries': (
        'data/02_intermediate/bridge_entries.parquet',
        'bridge_entries',
        'parquet'
    ),
    'aligned_matches': (
        'data/03_primary/aligned_matches.parquet',
        'aligned_matches',
        'parquet'
    ),
    'orphaned_entries': (
        'data/03_primary/orphaned_entries.parquet',
        'orphaned_entries',
        'parquet'
    ),
    'enriched_entries_raw': (
        'data/03_primary/enriched_entries_raw.parquet',
        'enriched_entries_raw',
        'parquet'
    ),
    'enriched_entries': (
        'data/03_primary/enriched_entries.parquet',
        'enriched_entries',
        'parquet'
    ),

    # Catalog metadata
    'gutenberg_catalog': (
        'data/01_raw/gutenberg_catalog.parquet',
        'gutenberg_catalog',
        'parquet'
    ),
    'benyehuda_catalog_raw': (
        'data/01_raw/benyehuda_catalog.parquet',
        'benyehuda_catalog_raw',
        'parquet'
    ),
    'benyehuda_catalog_enriched': (
        'data/02_intermediate/benyehuda_catalog_enriched.parquet',
        'benyehuda_catalog_enriched',
        'parquet'
    ),
    'aligned_catalogs': (
        'data/02_intermediate/aligned_catalogs.parquet',
        'aligned_catalogs',
        'parquet'
    ),
}


def get_engine():
    """Create SQLAlchemy engine."""
    return create_engine(CONNECTION_STRING)


def get_connection():
    """Create psycopg2 connection."""
    return psycopg2.connect(**DB_CONFIG)


def check_table_exists(table_name: str) -> bool:
    """Check if table exists in PostgreSQL."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = %s
                );
            """, (table_name,))
            return cur.fetchone()[0]
    finally:
        conn.close()


def get_table_row_count(table_name: str) -> int:
    """Get current row count in table."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table_name};")
            return cur.fetchone()[0]
    except Exception as e:
        logger.warning(f"Could not get row count for {table_name}: {e}")
        return 0
    finally:
        conn.close()


def load_data_file(file_path: str, file_type: str) -> Optional[pd.DataFrame]:
    """Load data from parquet or CSV file."""
    path = Path(file_path)

    if not path.exists():
        logger.warning(f"File not found: {file_path}")
        return None

    try:
        if file_type == 'parquet':
            df = pd.read_parquet(file_path)
        elif file_type == 'csv':
            df = pd.read_csv(file_path)
        else:
            logger.error(f"Unknown file type: {file_type}")
            return None

        logger.info(f"Loaded {len(df):,} rows from {file_path}")
        return df

    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        return None


def migrate_table(dataset_name: str, file_path: str, table_name: str, file_type: str, dry_run: bool = False) -> bool:
    """Migrate data from file to PostgreSQL table."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Migrating: {dataset_name}")
    logger.info(f"  File: {file_path}")
    logger.info(f"  Table: {table_name}")
    logger.info(f"{'='*60}")

    # Check if table exists
    if not check_table_exists(table_name):
        logger.error(f"❌ Table '{table_name}' does not exist in database!")
        logger.error(f"   Please run migrations first: docker-compose restart db")
        return False

    # Get current row count
    current_rows = get_table_row_count(table_name)
    logger.info(f"Current rows in {table_name}: {current_rows:,}")

    # Load data
    df = load_data_file(file_path, file_type)
    if df is None:
        return False

    if len(df) == 0:
        logger.warning(f"⚠️  File is empty, skipping")
        return True

    # Show preview
    logger.info(f"\nData preview:")
    logger.info(f"  Columns: {list(df.columns)}")
    logger.info(f"  Shape: {df.shape}")
    logger.info(f"  Memory: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")

    if dry_run:
        logger.info(f"\n✓ DRY RUN - Would migrate {len(df):,} rows to {table_name}")
        return True

    # Migrate data using pandas to_sql
    try:
        engine = get_engine()

        # Use append mode to preserve existing data
        logger.info(f"\nWriting {len(df):,} rows to PostgreSQL...")

        # Write in chunks for better performance
        chunk_size = 5000
        total_chunks = (len(df) + chunk_size - 1) // chunk_size

        with tqdm(total=len(df), desc=f"Migrating {dataset_name}") as pbar:
            for i in range(0, len(df), chunk_size):
                chunk = df.iloc[i:i+chunk_size]
                chunk.to_sql(
                    table_name,
                    engine,
                    if_exists='append',
                    index=False,
                    method='multi'
                )
                pbar.update(len(chunk))

        # Verify migration
        new_rows = get_table_row_count(table_name)
        added_rows = new_rows - current_rows

        logger.info(f"\n✅ Migration complete!")
        logger.info(f"   Rows added: {added_rows:,}")
        logger.info(f"   Total rows: {new_rows:,}")

        return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def migrate_all(dry_run: bool = False, skip_existing: bool = True):
    """Migrate all datasets."""
    logger.info(f"\n{'='*60}")
    logger.info(f"PostgreSQL Data Migration")
    logger.info(f"{'='*60}")
    logger.info(f"Dry run: {dry_run}")
    logger.info(f"Skip existing: {skip_existing}")
    logger.info(f"Total datasets: {len(MIGRATION_MAP)}")
    logger.info(f"{'='*60}\n")

    results = {}

    for dataset_name, (file_path, table_name, file_type) in MIGRATION_MAP.items():
        # Check if table already has data
        if skip_existing:
            try:
                row_count = get_table_row_count(table_name)
                if row_count > 0:
                    logger.info(f"⏭️  Skipping {dataset_name} - already has {row_count:,} rows")
                    results[dataset_name] = 'skipped'
                    continue
            except Exception as e:
                logger.warning(f"Could not check row count for {table_name}: {e}")

        success = migrate_table(dataset_name, file_path, table_name, file_type, dry_run)
        results[dataset_name] = 'success' if success else 'failed'

    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info(f"MIGRATION SUMMARY")
    logger.info(f"{'='*60}")

    success_count = sum(1 for r in results.values() if r == 'success')
    failed_count = sum(1 for r in results.values() if r == 'failed')
    skipped_count = sum(1 for r in results.values() if r == 'skipped')

    logger.info(f"✅ Success: {success_count}")
    logger.info(f"❌ Failed: {failed_count}")
    logger.info(f"⏭️  Skipped: {skipped_count}")
    logger.info(f"{'='*60}\n")

    if failed_count > 0:
        logger.error("\nFailed datasets:")
        for dataset, status in results.items():
            if status == 'failed':
                logger.error(f"  - {dataset}")

    return failed_count == 0


def main():
    parser = argparse.ArgumentParser(description='Migrate data from Parquet/CSV to PostgreSQL')
    parser.add_argument('--all', action='store_true', help='Migrate all datasets')
    parser.add_argument('--table', type=str, help='Migrate specific table')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be migrated without actually doing it')
    parser.add_argument('--force', action='store_true', help='Migrate even if table already has data')
    parser.add_argument('--list', action='store_true', help='List all available datasets')

    args = parser.parse_args()

    if args.list:
        logger.info("\nAvailable datasets:")
        for dataset_name, (file_path, table_name, file_type) in MIGRATION_MAP.items():
            logger.info(f"  {dataset_name:40s} → {table_name}")
        return 0

    if args.all:
        success = migrate_all(dry_run=args.dry_run, skip_existing=not args.force)
        return 0 if success else 1

    elif args.table:
        if args.table not in MIGRATION_MAP:
            logger.error(f"Unknown dataset: {args.table}")
            logger.info("\nAvailable datasets:")
            for dataset_name in MIGRATION_MAP.keys():
                logger.info(f"  - {dataset_name}")
            return 1

        file_path, table_name, file_type = MIGRATION_MAP[args.table]
        success = migrate_table(args.table, file_path, table_name, file_type, args.dry_run)
        return 0 if success else 1

    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
