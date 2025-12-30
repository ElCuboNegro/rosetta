import psycopg2
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Database connection
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "rosetta",
    "user": "postgres",
    "password": "rosetta_password",
}

TABLES_TO_FIX = [
    "raw_spanish_entries_unfiltered",
    "raw_hebrew_entries_unfiltered",
    "raw_spanish_entries_filtered",
    "raw_hebrew_entries_filtered",
    "raw_spanish_entries",
    "raw_hebrew_entries",
    "bridge_entries",
    "clean_examples",
    "wiktionary_examples_tagged",
    "tatoeba_examples_tagged",
    "aligned_book_sentences",
    "benyehuda_catalog_enriched",
    "aligned_catalogs",
    "aligned_matches",
    "orphaned_entries",
    "enriched_entries_raw",
    "enriched_entries",
    "sense_clusters",
    "cluster_metadata",
    "gutenberg_catalog",
    "benyehuda_catalog_raw",
    "book_validation_results",
]


def fix_table(cur, table_name):
    """Adds an 'id' column if it doesn't exist."""
    try:
        # Check if column exists
        cur.execute(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}' AND column_name = 'id';
        """)
        if cur.fetchone():
            logger.info(f"Table '{table_name}' already has an 'id' column. Skipping.")
            return

        logger.info(f"Adding 'id' column to table '{table_name}'...")
        # Add a serial id column. Postgres will auto-populate it.
        cur.execute(f"ALTER TABLE {table_name} ADD COLUMN id SERIAL PRIMARY KEY;")
        logger.info(f"Successfully fixed '{table_name}'.")
    except Exception as e:
        logger.error(f"Failed to fix table '{table_name}': {e}")


def main():
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        with conn.cursor() as cur:
            for table in TABLES_TO_FIX:
                # Check if table exists first
                cur.execute(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{table}'
                    );
                """)
                if cur.fetchone()[0]:
                    fix_table(cur, table)
                else:
                    logger.warning(f"Table '{table}' does not exist. Skipping.")

        logger.info("All tables processed.")
    except Exception as e:
        logger.error(f"Database connection error: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
