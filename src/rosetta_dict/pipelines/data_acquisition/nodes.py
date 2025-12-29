"""Nodes for downloading raw data sources.

This module provides functions for downloading pre-extracted Wiktionary data
from kaikki.org, which has already been processed with wiktextract.
"""

import logging
import urllib.request
import json
from typing import List, Dict, Any
from pathlib import Path
import time
from bs4 import BeautifulSoup
import requests
import re
import pandas as pd

logger = logging.getLogger(__name__)

# Mapping of language codes to full language names for kaikki.org URLs
LANGUAGE_NAMES = {
    "es": "Spanish",
    "he": "Hebrew",
    "en": "English",
    "fr": "French",
    "de": "German",
}


def download_kaikki_data(language_code: str, output_path: str) -> str:
    """Download pre-extracted Wiktionary data from kaikki.org.

    kaikki.org provides Wiktionary data already processed with wiktextract,
    with all templates and Lua modules expanded. This is much faster and
    more reliable than parsing XML dumps directly.

    Args:
        language_code: Two-letter language code (e.g., 'es' for Spanish, 'he' for Hebrew).
        output_path: Local path where the JSONL file should be saved.

    Returns:
        Path to the downloaded file.

    Raises:
        urllib.error.URLError: If download fails.
    """
    output_file = Path(output_path)

    # Check if file already exists
    if output_file.exists():
        file_size_mb = output_file.stat().st_size / (1024 * 1024)
        logger.info(f"Kaikki data already exists: {output_path} ({file_size_mb:.1f} MB)")
        return output_path

    # Create directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Get full language name for URL
    language_name = LANGUAGE_NAMES.get(language_code)
    if not language_name:
        raise ValueError(
            f"Unsupported language code: {language_code}. "
            f"Supported codes: {list(LANGUAGE_NAMES.keys())}"
        )

    # Construct kaikki.org URL using language name
    # Format: https://kaikki.org/dictionary/{LanguageName}/kaikki.org-dictionary-{LanguageName}.jsonl
    url = (
        f"https://kaikki.org/dictionary/{language_name}/kaikki.org-dictionary-{language_name}.jsonl"
    )

    import time

    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(
                f"Downloading {language_name} Wiktionary from {url} (Attempt {attempt + 1}/{max_retries})..."
            )

            # Download with progress reporting
            def report_progress(block_num: int, block_size: int, total_size: int) -> None:
                if total_size > 0:
                    downloaded_mb = (block_num * block_size) / (1024 * 1024)
                    total_mb = total_size / (1024 * 1024)
                    if block_num % 50 == 0:  # Report every ~5MB
                        logger.info(f"Downloaded {downloaded_mb:.1f} MB / {total_mb:.1f} MB")

            urllib.request.urlretrieve(url, output_path, reporthook=report_progress)

            file_size_mb = output_file.stat().st_size / (1024 * 1024)
            logger.info(f"Download complete: {output_path} ({file_size_mb:.1f} MB)")
            return output_path

        except (urllib.error.ContentTooShortError, urllib.error.URLError) as e:
            logger.warning(f"Download failed (attempt {attempt + 1}/{max_retries}): {e}")

            # Clean up partial download with robust retry for Windows
            if output_file.exists():
                for i in range(5):
                    try:
                        output_file.unlink()
                        break
                    except PermissionError:
                        time.sleep(1)
                else:
                    logger.warning(
                        f"Could not delete partial file {output_path}. Please delete manually."
                    )

            if attempt < max_retries - 1:
                logger.info("Retrying in 5 seconds...")
                time.sleep(5)
            else:
                logger.error(f"Failed to download {url} after {max_retries} attempts.")
                raise

        except Exception as e:
            logger.error(f"Unexpected error downloading {url}: {e}")
            if output_file.exists():
                try:
                    output_file.unlink()
                except:
                    pass
            raise


def download_gutenberg_data(languages: list[str], output_dir: str, limit: int = 20) -> list[str]:
    """
    Download books from Project Gutenberg via Gutendex API.

    Args:
        languages: List of language codes (e.g. ['es', 'he']).
        output_dir: Base directory to save books.
        limit: Max books per language to download.

    Returns:
        List of paths to downloaded files.
    """
    import requests
    import time

    downloaded_files = []
    base_path = Path(output_dir)

    for lang in languages:
        lang_dir = base_path / lang
        lang_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Searching Gutenberg for language: {lang}")
        # Gutendex API search
        api_url = f"https://gutendex.com/books?languages={lang}&sort=popular"

        books_downloaded = 0
        page_url = api_url

        while books_downloaded < limit and page_url:
            try:
                response = requests.get(page_url)
                response.raise_for_status()
                data = response.json()

                books = data.get("results", [])
                if not books:
                    break

                for book in books:
                    if books_downloaded >= limit:
                        break

                    title = book.get("title", "Unknown").replace(":", "-").replace("/", "-")[:50]
                    book_id = book.get("id")

                    # Find text/plain format (loose matching)
                    formats = book.get("formats", {})
                    text_url = None

                    # Prioritize UTF-8
                    for fmt, url in formats.items():
                        if "text/plain" in fmt and "utf-8" in fmt:
                            text_url = url
                            break

                    # Fallback to any text/plain
                    if not text_url:
                        for fmt, url in formats.items():
                            if "text/plain" in fmt:
                                text_url = url
                                break

                    if not text_url:
                        # logger.debug(f"Skipping {title}: No text/plain format found. Available: {list(formats.keys())}")
                        continue

                    filename = f"{book_id}_{title}.txt"
                    file_path = lang_dir / filename

                    if file_path.exists():
                        # logger.info(f"Skipping existing book: {filename}")
                        downloaded_files.append(str(file_path))
                        books_downloaded += 1
                        continue

                    logger.info(f"Downloading: {title} ({lang})")
                    try:
                        book_content = requests.get(text_url).text
                        file_path.write_text(book_content, encoding="utf-8")
                        downloaded_files.append(str(file_path))
                        books_downloaded += 1
                        time.sleep(0.5)  # Be nice to servers
                    except Exception as e:
                        logger.warning(f"Failed to download {title}: {e}")

                page_url = data.get("next")

            except Exception as e:
                logger.error(f"Error querying Gutendex: {e}")
                break

    return downloaded_files


def download_benyehuda_data(
    output_dir: str, limit: int = 20, languages: list[str] = None
) -> list[str]:
    """
    Download Hebrew translated works from Ben Yehuda project.

    Args:
        output_dir: Directory to save the works.
        limit: Maximum number of works to download.
        languages: List of source language codes to filter by (e.g. ['en', 'es']).

    Returns:
        List of paths to downloaded JSON files.
    """
    import json

    downloaded_files = []
    output_path = Path(output_dir) / "ben_yehuda"
    output_path.mkdir(parents=True, exist_ok=True)

    base_url = "https://benyehuda.org"
    search_url = f"{base_url}/works"

    # Build params dict
    params = {"sort_by": "alphabetical_asc"}
    if languages:
        params["ckb_languages[]"] = languages

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    )

    works_processed = 0
    # Initial request will use params, subsequent pagination might use full URLs from 'next' links
    # So we handle the first request differently or just loop

    current_page_url = search_url
    first_request = True

    while works_processed < limit and current_page_url:
        logger.info(f"Processing search page: {current_page_url}")
        try:
            if first_request:
                response = session.get(current_page_url, params=params)
                first_request = False
            else:
                response = session.get(current_page_url)

            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Find work links
            work_links = []
            # Selector from research: ol li a[href^='/read/']
            # We can use a broader select to be safe
            for a in soup.select("a[href^='/read/']"):
                if "/read/" in a["href"] and "read" not in a.text:  # Avoid navigation links if any
                    work_links.append(a["href"])

            # Unique links
            work_links = list(set(work_links))

            for rel_link in work_links:
                if works_processed >= limit:
                    break

                work_id = rel_link.split("/")[-1]
                file_path = output_path / f"{work_id}.json"

                if file_path.exists():
                    logger.info(f"Skipping existing Ben Yehuda work: {work_id}")
                    downloaded_files.append(str(file_path))
                    works_processed += 1
                    continue

                work_url = f"{base_url}{rel_link}"
                logger.info(f"Processing work: {work_url}")

                try:
                    # 1. Get work page for metadata and token
                    w_resp = session.get(work_url)
                    w_resp.raise_for_status()
                    w_soup = BeautifulSoup(w_resp.text, "html.parser")

                    # Metadata extraction
                    title = w_soup.title.string if w_soup.title else "Unknown"

                    metadata_entries = []
                    for meta in w_soup.select(".metadata"):
                        text = meta.get_text(strip=True)
                        if text:
                            metadata_entries.append(text)

                    # Attempt to parse specific fields
                    original_title = None
                    for entry in metadata_entries:
                        # Common patterns for original title
                        # Note: This is heuristic and depends on exact site wording
                        if "מקור" in entry or "Translated" in entry:
                            # Store potential candidates
                            pass

                    # Extract authenticity_token for download
                    token = None
                    form = w_soup.find("form", action=lambda x: x and "download" in x)
                    if form:
                        token_input = form.find("input", {"name": "authenticity_token"})
                        if token_input:
                            token = token_input["value"]

                    if not token:
                        token_input = w_soup.find("input", {"name": "authenticity_token"})
                        if token_input:
                            token = token_input["value"]

                    if not token:
                        logger.warning(
                            f"Could not find download token for {work_id}, skipping download."
                        )
                        continue

                    # 2. Download Text via POST
                    download_url = f"{base_url}/download/{work_id}"
                    payload = {"authenticity_token": token, "format": "txt", "commit": "הורדה"}

                    dl_resp = session.post(download_url, data=payload)
                    dl_resp.encoding = "utf-8"  # Force UTF-8 for Hebrew content

                    content = ""
                    if dl_resp.status_code == 200:
                        content = dl_resp.text
                    else:
                        logger.warning(
                            f"Failed to download text for {work_id}: {dl_resp.status_code}"
                        )
                        continue

                    # Construct data object
                    data = {
                        "id": work_id,
                        "url": work_url,
                        "title": title,
                        "content": content,
                        "metadata": {"scraped_at": time.time(), "raw_metadata": metadata_entries},
                    }

                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

                    downloaded_files.append(str(file_path))
                    works_processed += 1

                    time.sleep(1)  # Be nice

                except Exception as e:
                    logger.error(f"Error processing work {work_id}: {e}")

            # Find next page
            # Selector: .browse_paging -> finding "Next" or checking href
            # Simple check for now: look for link with text "לדף הבא" (to next page) or similar
            next_link = None
            pagination = soup.select_one(".browse_paging")
            if pagination:
                for a in pagination.find_all("a"):
                    if "הבא" in a.text or "next" in a.text.lower():
                        next_link = a["href"]
                        break

            if next_link:
                if next_link.startswith("http"):
                    current_page_url = next_link
                else:
                    current_page_url = f"{base_url}{next_link}"
            else:
                current_page_url = None

        except Exception as e:
            logger.error(f"Error processing search page: {e}")
            break

    return downloaded_files


def download_books_from_matches(
    matches_df: pd.DataFrame, output_dir: str = "data/01_raw/gutenberg_counterparts"
) -> List[str]:
    """
    Download Gutenberg books based on aligned matches.

    Args:
        matches_df: DataFrame containing 'gutenberg_id' column.
        output_dir: Directory to save downloaded books.

    Returns:
        List of paths to downloaded files.
    """
    if matches_df.empty:
        logger.warning("No matches provided for download.")
        return []

    # Extract unique IDs
    # matches_df should have 'gutenberg_id'.
    if "gutenberg_id" not in matches_df.columns:
        logger.error("matches_df missing 'gutenberg_id' column.")
        return []

    gutenberg_ids = matches_df["gutenberg_id"].dropna().unique().tolist()
    logger.info(f"Downloading {len(gutenberg_ids)} Gutenberg books from matches...")

    base_path = Path(output_dir)
    base_path.mkdir(parents=True, exist_ok=True)

    downloaded_files = []

    # Batch processing (Gutendex supports multiple IDs)
    batch_size = 32

    for i in range(0, len(gutenberg_ids), batch_size):
        batch = gutenberg_ids[i : i + batch_size]
        ids_str = ",".join(map(str, batch))

        url = f"https://gutendex.com/books?ids={ids_str}"

        try:
            resp = requests.get(url)
            if resp.status_code != 200:
                logger.error(f"Failed to fetch metadata for batch {i}: {resp.status_code}")
                continue

            data = resp.json()
            results = data.get("results", [])

            for book in results:
                book_id = book["id"]
                title = book["title"][:50].replace(":", "-").replace("/", "-")
                lang = book["languages"][0] if book.get("languages") else "unknown"

                # Language subfolder?
                lang_dir = base_path / lang
                lang_dir.mkdir(exist_ok=True)

                filename = f"{book_id}_{title}.txt"
                file_path = lang_dir / filename

                if file_path.exists():
                    downloaded_files.append(str(file_path))
                    continue

                # Find text url
                text_url = None
                for fmt, link in book["formats"].items():
                    if "text/plain" in fmt and "utf-8" in fmt:
                        text_url = link
                        break
                if not text_url:
                    for fmt, link in book["formats"].items():
                        if "text/plain" in fmt:
                            text_url = link
                            break

                if text_url:
                    try:
                        dl_resp = requests.get(text_url)
                        dl_resp.encoding = "utf-8"
                        file_path.write_text(dl_resp.text, encoding="utf-8")
                        downloaded_files.append(str(file_path))
                        logger.info(f"Downloaded: {filename}")
                        time.sleep(0.2)
                    except Exception as e:
                        logger.warning(f"Failed to download content for {book_id}: {e}")
                else:
                    logger.warning(f"No text format for book {book_id}")

            time.sleep(0.5)

        except Exception as e:
            logger.error(f"Error processing batch {i}: {e}")

    return downloaded_files
