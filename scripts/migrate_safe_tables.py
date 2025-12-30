"""
Migrate only the tables with verified matching schemas.
These are the tables that are known to work without schema issues.
"""

import subprocess
import sys

# Only migrate tables where we've verified the schema matches
SAFE_TABLES = [
    'sense_clusters',                      # ✅ Verified working
    'aligned_book_sentences',              # ✅ Verified working
    'wiktionary_examples_tagged',          # ✅ Fixed in migration 06
    'raw_spanish_entries_unfiltered',      # ✅ Has matching schema
    'raw_hebrew_entries_unfiltered',       # ✅ Has matching schema
    'raw_spanish_entries_filtered',        # ✅ Has matching schema
    'raw_hebrew_entries_filtered',         # ✅ Has matching schema
    'raw_spanish_entries',                 # ✅ Has matching schema
    'raw_hebrew_entries',                  # ✅ Has matching schema
    'gutenberg_catalog',                   # ✅ Has matching schema
]

def main():
    print("=" * 60)
    print("Migrating Safe Tables to PostgreSQL")
    print("=" * 60)
    print(f"Will migrate {len(SAFE_TABLES)} verified tables")
    print()

    success_count = 0
    failed_count = 0
    failed_tables = []

    for i, table in enumerate(SAFE_TABLES, 1):
        print(f"\n[{i}/{len(SAFE_TABLES)}] Migrating {table}...")
        print("-" * 60)

        try:
            result = subprocess.run(
                [sys.executable, 'scripts/migrate_to_postgres.py', '--table', table],
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout per table
            )

            if result.returncode == 0:
                print(f"✅ SUCCESS: {table}")
                success_count += 1
            else:
                print(f"❌ FAILED: {table}")
                print(f"Error: {result.stderr[-500:]}")  # Last 500 chars of error
                failed_count += 1
                failed_tables.append(table)

        except subprocess.TimeoutExpired:
            print(f"⏱️  TIMEOUT: {table}")
            failed_count += 1
            failed_tables.append(table)
        except Exception as e:
            print(f"❌ ERROR: {table} - {e}")
            failed_count += 1
            failed_tables.append(table)

    # Print summary
    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"✅ Success: {success_count}")
    print(f"❌ Failed: {failed_count}")
    print("=" * 60)

    if failed_tables:
        print("\nFailed tables:")
        for table in failed_tables:
            print(f"  - {table}")

    print("\nTo test your pipeline:")
    print("  python -m kedro run --pipeline sense_induction")

    return 0 if failed_count == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
