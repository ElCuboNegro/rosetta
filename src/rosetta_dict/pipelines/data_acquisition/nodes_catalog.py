import requests
import logging
import pandas as pd
from typing import List, Dict, Any
import time
import os


logger = logging.getLogger(__name__)


def fetch_gutenberg_catalog(languages: List[str] = ["es", "en"], limit: int = None) -> pd.DataFrame:
    """
    Fetch full catalog metadata from Gutendex for specified languages.
    Iterates through all pages up to optional limit (books count per language).
    """
    base_url = "https://gutendex.com/books"
    all_books = []

    for lang in languages:
        logger.info(f"Fetching Gutenberg catalog for language: {lang}")
        url = f"{base_url}?languages={lang}"
        page = 1
        count_lang = 0

        while url:
            if limit and count_lang >= limit:
                logger.info(f"Reached limit of {limit} books for {lang}.")
                break

            if page % 10 == 0:
                logger.info(f"Fetching page {page} for {lang}...")

            try:
                resp = requests.get(url)
                if resp.status_code != 200:
                    logger.error(f"Failed to fetch {url}: {resp.status_code}")
                    break

                data = resp.json()
                results = data.get("results", [])

                for book in results:
                    # Extract authors (semicolon sep)
                    authors = "; ".join([p.get("name", "") for p in book.get("authors", [])])

                    all_books.append(
                        {
                            "gutenberg_id": book["id"],
                            "title": book["title"],
                            "authors": authors,
                            "language": lang,
                            "download_count": book.get("download_count", 0),
                        }
                    )
                    count_lang += 1

                url = data.get("next")
                page += 1
                time.sleep(0.1)  # Polite delay

            except Exception as e:
                logger.error(f"Error fetching page {page}: {e}")
                break

    df = pd.DataFrame(all_books)
    logger.info(f"Fetched Gutenberg catalog with {len(df)} entries.")
    return df


def build_benyehuda_catalog(dump_path: str = "data/01_raw/ben_yehuda_dump") -> pd.DataFrame:
    """
    Parse the local Ben Yehuda dump to build a catalog using pseudocatalogue.csv.
    """
    logger.info(f"Building Ben Yehuda catalog from: {dump_path}")

    csv_path = os.path.join(dump_path, "pseudocatalogue.csv")
    if not os.path.exists(csv_path):
        logger.warning(f"Metadata CSV not found: {csv_path}. Cloning required.")
        return pd.DataFrame()

    try:
        df = pd.read_csv(csv_path)
        logger.info(f"Loaded {len(df)} records from {csv_path}")

        # Construct absolute file paths
        # structure: dump_path/txt_stripped/pXXX/mYYY.txt
        # 'path' column in CSV is like /pXXX/mYYY
        def get_file_path(rel_path):
            # Remove leading slash if exists
            if rel_path.startswith("/"):
                rel_path = rel_path[1:]

            # Append .txt if not present (CSV path usually doesn't have extension)
            # The folder structure observed is .../txt_stripped/pXXX/mYYY.txt

            full_path = os.path.join(dump_path, "txt_stripped", rel_path + ".txt")
            return full_path.replace("\\", "/")

        df["file_path"] = df["path"].apply(get_file_path)

        # Rename columns to standard schema if needed
        df = df.rename(
            columns={
                "ID": "benyehuda_id",
                "authors": "author",
                "original_language": "language_origin",
            }
        )

        # Filter existence?
        # df["exists"] = df["file_path"].apply(os.path.exists)
        # logger.info(f"Files found: {df['exists'].sum()} out of {len(df)}")

        return df

    except Exception as e:
        logger.error(f"Failed to read Ben Yehuda catalog CSV: {e}")
        return pd.DataFrame()
