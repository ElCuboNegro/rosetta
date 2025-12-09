"""Nodes for downloading raw data sources.

This module provides functions for downloading pre-extracted Wiktionary data
from kaikki.org, which has already been processed with wiktextract.
"""

import logging
import urllib.request
from pathlib import Path

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
    url = f"https://kaikki.org/dictionary/{language_name}/kaikki.org-dictionary-{language_name}.jsonl"

    import time
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"Downloading {language_name} Wiktionary from {url} (Attempt {attempt+1}/{max_retries})...")
            
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
            logger.warning(f"Download failed (attempt {attempt+1}/{max_retries}): {e}")
            
            # Clean up partial download with robust retry for Windows
            if output_file.exists():
                for i in range(5):
                    try:
                        output_file.unlink()
                        break
                    except PermissionError:
                        time.sleep(1)
                else:
                    logger.warning(f"Could not delete partial file {output_path}. Please delete manually.")
            
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
