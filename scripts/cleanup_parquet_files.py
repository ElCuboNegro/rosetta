"""
Clean up parquet files that are now stored in PostgreSQL.

This script:
1. Verifies data exists in PostgreSQL before removal
2. Creates a backup archive of parquet files
3. Removes parquet files that are safely in the database
"""
import psycopg2
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

# Set UTF-8 encoding for console output on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Use credentials from conf/local/credentials.yml
conn = psycopg2.connect('postgresql://postgres:rosetta_password@localhost:5432/rosetta')
cur = conn.cursor()

# Mapping of parquet files to their PostgreSQL tables
PARQUET_TO_TABLE_MAP = {
    # Raw data
    "data/01_raw/benyehuda_catalog.parquet": "benyehuda_catalog_raw",
    "data/01_raw/gutenberg_catalog.parquet": "gutenberg_catalog",

    # Intermediate data
    "data/02_intermediate/aligned_books.parquet": None,  # Not in DB yet
    "data/02_intermediate/aligned_catalogs.parquet": "aligned_catalogs",
    "data/02_intermediate/bridge_entries.parquet": "bridge_entries",
    "data/02_intermediate/clean_examples.parquet": "clean_examples",
    "data/02_intermediate/raw_hebrew_entries.parquet": "raw_hebrew_entries",
    "data/02_intermediate/raw_hebrew_entries_filtered.parquet": "raw_hebrew_entries_filtered",
    "data/02_intermediate/raw_hebrew_entries_unfiltered.parquet": "raw_hebrew_entries_unfiltered",
    "data/02_intermediate/raw_spanish_entries.parquet": "raw_spanish_entries",
    "data/02_intermediate/raw_spanish_entries_filtered.parquet": "raw_spanish_entries_filtered",
    "data/02_intermediate/raw_spanish_entries_unfiltered.parquet": "raw_spanish_entries_unfiltered",
    "data/02_intermediate/tatoeba_examples_tagged.parquet": "tatoeba_examples_tagged",

    # Primary data
    "data/03_primary/aligned_matches.parquet": "aligned_matches",
    "data/03_primary/enriched_entries.parquet": "enriched_entries",
    "data/03_primary/enriched_entries_raw.parquet": "enriched_entries_raw",

    # Feature data
    "data/04_feature/sense_clusters.parquet": "sense_clusters",
}

def verify_table_has_data(table_name):
    """Check if a PostgreSQL table exists and has data."""
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cur.fetchone()[0]
        return count > 0
    except Exception as e:
        print(f"  ⚠️  Error checking table {table_name}: {e}")
        return False

def get_file_size_mb(filepath):
    """Get file size in MB."""
    if os.path.exists(filepath):
        return os.path.getsize(filepath) / (1024 * 1024)
    return 0

print("=" * 80)
print("Parquet File Cleanup - PostgreSQL Migration")
print("=" * 80)
print()

# Create backup directory
backup_dir = Path("data/parquet_backup_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
backup_dir.mkdir(parents=True, exist_ok=True)
print(f"📦 Backup directory: {backup_dir}")
print()

files_to_remove = []
files_to_keep = []
total_size_to_free = 0

print("Analyzing parquet files:")
print("-" * 80)

for parquet_file, table_name in PARQUET_TO_TABLE_MAP.items():
    if not os.path.exists(parquet_file):
        print(f"⏭️  SKIP: {parquet_file} (file not found)")
        continue

    file_size = get_file_size_mb(parquet_file)

    # Check if table_name is None or table doesn't have data
    if table_name is None:
        print(f"⚠️  KEEP: {parquet_file} ({file_size:.1f} MB) - No DB table mapped")
        files_to_keep.append(parquet_file)
    elif verify_table_has_data(table_name):
        print(f"✅ SAFE TO REMOVE: {parquet_file} ({file_size:.1f} MB)")
        print(f"   → Data exists in PostgreSQL table: {table_name}")
        files_to_remove.append(parquet_file)
        total_size_to_free += file_size
    else:
        print(f"⚠️  KEEP: {parquet_file} ({file_size:.1f} MB) - Table '{table_name}' is empty")
        files_to_keep.append(parquet_file)

print()
print("=" * 80)
print(f"Summary:")
print(f"  Files safe to remove: {len(files_to_remove)}")
print(f"  Files to keep: {len(files_to_keep)}")
print(f"  Total space to free: {total_size_to_free:.1f} MB")
print("=" * 80)
print()

if files_to_remove:
    response = input("Proceed with cleanup? (yes/no): ").strip().lower()

    if response == 'yes':
        print()
        print("Starting cleanup...")
        print("-" * 80)

        # Backup and remove files
        for parquet_file in files_to_remove:
            try:
                # Create backup
                rel_path = Path(parquet_file).relative_to("data")
                backup_path = backup_dir / rel_path
                backup_path.parent.mkdir(parents=True, exist_ok=True)

                shutil.copy2(parquet_file, backup_path)
                print(f"📋 Backed up: {parquet_file}")

                # Remove original
                os.remove(parquet_file)
                print(f"🗑️  Removed: {parquet_file}")

            except Exception as e:
                print(f"❌ Error processing {parquet_file}: {e}")

        print()
        print("✅ Cleanup complete!")
        print(f"📦 Backups saved to: {backup_dir}")
        print(f"💾 Space freed: {total_size_to_free:.1f} MB")
    else:
        print("Cleanup cancelled.")
else:
    print("No files to remove.")

conn.close()
