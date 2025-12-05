"""Harvester pipeline nodes for parsing Wiktionary and Tatoeba data.

This module uses wiktextract to parse real Wiktionary dumps and extract
Spanish and Hebrew word entries with IPA, definitions, and translations.
"""

import logging
import os
from pathlib import Path
import urllib.request
import pandas as pd
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def download_wiktionary_dump(url: str, output_path: str) -> str:
    """Download a Wiktionary dump file if it doesn't already exist.
    
    Args:
        url: URL to download the dump from
        output_path: Local path where the dump should be saved
        
    Returns:
        Path to the downloaded file
        
    Raises:
        urllib.error.URLError: If download fails
    """
    output_file = Path(output_path)
    
    # Check if file already exists
    if output_file.exists():
        file_size_mb = output_file.stat().st_size / (1024 * 1024)
        logger.info(f"Dump file already exists: {output_path} ({file_size_mb:.1f} MB)")
        return output_path
    
    # Create directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Downloading Wiktionary dump from {url}...")
    logger.info(f"This may take several minutes (file is ~100-350 MB)...")
    
    try:
        # Download with progress reporting
        def report_progress(block_num, block_size, total_size):
            downloaded_mb = (block_num * block_size) / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            if block_num % 100 == 0:  # Report every ~10MB
                logger.info(f"Downloaded {downloaded_mb:.1f} MB / {total_mb:.1f} MB")
        
        urllib.request.urlretrieve(url, output_path, reporthook=report_progress)
        
        file_size_mb = output_file.stat().st_size / (1024 * 1024)
        logger.info(f"Download complete: {output_path} ({file_size_mb:.1f} MB)")
        return output_path
        
    except Exception as e:
        # Clean up partial download
        if output_file.exists():
            output_file.unlink()
        logger.error(f"Failed to download {url}: {e}")
        raise



def parse_spanish_wiktionary(wiktionary_dump_path: str) -> pd.DataFrame:
    """Parse Spanish Wiktionary dump into structured entries using wiktextract.
    
    Extracts Spanish words with IPA pronunciations, definitions, POS tags,
    and Hebrew translations from a Wiktionary XML dump.
    
    Args:
        wiktionary_dump_path: Path to Spanish Wiktionary XML dump file.
        
    Returns:
        DataFrame with columns: word, pos, ipa, definitions (list), 
        translations_he (list of Hebrew translations).
        
    Raises:
        ImportError: If wiktextract is not installed.
        FileNotFoundError: If dump file doesn't exist.
    """
    logger.info(f"Parsing Spanish Wiktionary from {wiktionary_dump_path}...")
    
    from wiktextract import WiktionaryConfig, parse_wiktionary
    from wikitextprocessor import Wtp
    
    # Create Wiktextract context for Spanish Wiktionary
    # Use num_threads=1 to avoid nested multiprocessing issues when running with Kedro ParallelRunner
    ctx = Wtp(num_threads=1)
    
    # Configure wiktextract for Spanish Wiktionary
    config = WiktionaryConfig(
        capture_languages=["Spanish", "Hebrew", "English", "French", "German"],
        capture_translations=True,
        capture_pronunciation=True,
        capture_linkages=True,
        capture_examples=True
    )
    
    # Parse the dump with callback to collect entries and track progress
    entries = []
    entry_count = [0]  # Use list to allow modification in nested function

    def word_callback(word_data):
        entries.append(word_data)
        entry_count[0] += 1
        # Log progress every 1000 entries
        if entry_count[0] % 1000 == 0:
            logger.info(f"Parsed {entry_count[0]} entries so far...")

    logger.info("Starting wiktextract parsing (this may take several minutes)...")
    parse_wiktionary(ctx, wiktionary_dump_path, config, word_callback)
    logger.info(f"Parsing complete. Total entries processed: {entry_count[0]}")

    # Extract relevant data
    data = []
    spanish_entries = 0
    entries_with_definitions = 0

    for entry in entries:
        # Only process Spanish language entries
        if entry.get("lang_code") != "es":
            continue

        spanish_entries += 1

        word = entry.get("word", "")
        if not word:
            continue

        # Get IPA pronunciation
        ipa = ""
        sounds = entry.get("sounds", [])
        for sound in sounds:
            if "ipa" in sound:
                ipa = sound["ipa"]
                break

        # Get part of speech
        pos = entry.get("pos", "unknown")

        # Get definitions (senses)
        definitions = []
        senses = entry.get("senses", [])
        for sense in senses:
            gloss = sense.get("glosses", [""])[0]
            if gloss:
                definitions.append(gloss)

        # Get all translations (English, French, German, Hebrew for triangulation)
        translations_en = []
        translations_fr = []
        translations_de = []
        translations_he = []
        translations = entry.get("translations", [])
        for trans in translations:
            lang_code = trans.get("lang_code")
            trans_word = trans.get("word", "")
            if not trans_word:
                continue

            if lang_code == "en" and trans_word not in translations_en:
                translations_en.append(trans_word)
            elif lang_code == "fr" and trans_word not in translations_fr:
                translations_fr.append(trans_word)
            elif lang_code == "de" and trans_word not in translations_de:
                translations_de.append(trans_word)
            elif lang_code == "he" and trans_word not in translations_he:
                translations_he.append(trans_word)

        # Add ALL entries, even without definitions (we can use word itself as definition)
        if not definitions:
            definitions = [word]  # Use word as its own definition if no gloss available

        entries_with_definitions += 1

        data.append({
            "word": word,
            "pos": pos,
            "ipa": ipa,
            "definitions": definitions,
            "translations_en": translations_en,
            "translations_fr": translations_fr,
            "translations_de": translations_de,
            "translations_he": translations_he
        })
    
    df = pd.DataFrame(data)
    logger.info(f"Found {spanish_entries} Spanish entries out of {entry_count[0]} total entries")
    logger.info(f"Kept {len(df)} Spanish entries")
    logger.info(f"Entries with Hebrew translations: {df['translations_he'].apply(len).sum()}")
    return df


def parse_hebrew_wiktionary(wiktionary_dump_path: str) -> pd.DataFrame:
    """Parse Hebrew Wiktionary dump into structured entries using wiktextract.
    
    Args:
        wiktionary_dump_path: Path to Hebrew Wiktionary XML dump file.
        
    Returns:
        DataFrame with columns: word, pos, ipa, definitions (list),
        translations_es (list of Spanish translations).
        
    Raises:
        ImportError: If wiktextract is not installed.
        FileNotFoundError: If dump file doesn't exist.
    """
    logger.info(f"Parsing Hebrew Wiktionary from {wiktionary_dump_path}...")
    
    from wiktextract import WiktionaryConfig, parse_wiktionary
    from wikitextprocessor import Wtp
    
    # Create Wiktextract context for Hebrew Wiktionary
    # Use num_threads=1 to avoid nested multiprocessing issues when running with Kedro ParallelRunner
    ctx = Wtp(num_threads=1)
    
    # Configure wiktextract for Hebrew Wiktionary
    config = WiktionaryConfig(
        capture_languages=["Hebrew", "Spanish", "English", "French", "German"],
        capture_translations=True,
        capture_pronunciation=True,
        capture_linkages=True,
        capture_examples=True
    )
    
    # Parse the dump with callback to collect entries and track progress
    entries = []
    entry_count = [0]  # Use list to allow modification in nested function

    def word_callback(word_data):
        entries.append(word_data)
        entry_count[0] += 1
        # Log progress every 1000 entries
        if entry_count[0] % 1000 == 0:
            logger.info(f"Parsed {entry_count[0]} entries so far...")

    logger.info("Starting wiktextract parsing (this may take several minutes)...")
    parse_wiktionary(ctx, wiktionary_dump_path, config, word_callback)
    logger.info(f"Parsing complete. Total entries processed: {entry_count[0]}")

    # Extract relevant data
    data = []
    hebrew_entries = 0
    entries_with_definitions = 0

    for entry in entries:
        # Only process Hebrew language entries
        if entry.get("lang_code") != "he":
            continue

        hebrew_entries += 1

        word = entry.get("word", "")
        if not word:
            continue

        # Get IPA pronunciation
        ipa = ""
        sounds = entry.get("sounds", [])
        for sound in sounds:
            if "ipa" in sound:
                ipa = sound["ipa"]
                break

        # Get part of speech
        pos = entry.get("pos", "unknown")

        # Get definitions (senses)
        definitions = []
        senses = entry.get("senses", [])
        for sense in senses:
            gloss = sense.get("glosses", [""])[0]
            if gloss:
                definitions.append(gloss)

        # Get all translations (English, French, German, Spanish for triangulation)
        translations_en = []
        translations_fr = []
        translations_de = []
        translations_es = []
        translations = entry.get("translations", [])
        for trans in translations:
            lang_code = trans.get("lang_code")
            trans_word = trans.get("word", "")
            if not trans_word:
                continue

            if lang_code == "en" and trans_word not in translations_en:
                translations_en.append(trans_word)
            elif lang_code == "fr" and trans_word not in translations_fr:
                translations_fr.append(trans_word)
            elif lang_code == "de" and trans_word not in translations_de:
                translations_de.append(trans_word)
            elif lang_code == "es" and trans_word not in translations_es:
                translations_es.append(trans_word)

        # Add ALL entries, even without definitions (we can use word itself as definition)
        if not definitions:
            definitions = [word]  # Use word as its own definition if no gloss available

        entries_with_definitions += 1

        data.append({
            "word": word,
            "pos": pos,
            "ipa": ipa,
            "definitions": definitions,
            "translations_en": translations_en,
            "translations_fr": translations_fr,
            "translations_de": translations_de,
            "translations_es": translations_es
        })
    
    df = pd.DataFrame(data)
    logger.info(f"Found {hebrew_entries} Hebrew entries out of {entry_count[0]} total entries")
    logger.info(f"Kept {len(df)} Hebrew entries")
    logger.info(f"Entries with Spanish translations: {df['translations_es'].apply(len).sum()}")
    return df


def process_tatoeba(tatoeba_df: pd.DataFrame) -> pd.DataFrame:
    """Process Tatoeba sentence pairs for Spanish-Hebrew examples.
    
    This function processes the raw Tatoeba sentences DataFrame to extract
    Spanish-Hebrew sentence pairs. It uses simple word extraction (splitting
    on whitespace) to associate words with sentences.
    
    Args:
        tatoeba_df: Raw Tatoeba data with columns [id, lang, text].
        
    Returns:
        DataFrame with columns: es (Spanish text), he (Hebrew text),
        es_words (list of Spanish words), he_words (list of Hebrew words).
        
    Note:
        For production use with large Tatoeba dumps, you'll need translation
        link data to properly pair Spanish and Hebrew sentences. This implementation
        assumes the input is pre-filtered for Spanish-Hebrew pairs.
    """
    logger.info("Processing Tatoeba sentences...")
    
    # Filter for Spanish and Hebrew sentences
    es_sentences = tatoeba_df[tatoeba_df['lang'] == 'es'].copy()
    he_sentences = tatoeba_df[tatoeba_df['lang'] == 'he'].copy()
    
    logger.info(f"Found {len(es_sentences)} Spanish and {len(he_sentences)} Hebrew sentences")
    
    # For this implementation, we'll pair sentences by index
    # In production, you would use Tatoeba's links.csv to find actual translation pairs
    examples = []
    
    for idx in range(min(len(es_sentences), len(he_sentences))):
        es_row = es_sentences.iloc[idx]
        he_row = he_sentences.iloc[idx]
        
        es_text = str(es_row['text'])
        he_text = str(he_row['text'])
        
        # Extract words (simple tokenization)
        es_words = [w.strip('.,!?;:()[]"\'').lower() for w in es_text.split() if len(w) > 2]
        he_words = [w.strip('.,!?;:()[]"\'') for w in he_text.split() if len(w) > 1]
        
        examples.append({
            "es": es_text,
            "he": he_text,
            "es_words": es_words,
            "he_words": he_words
        })
    
    df = pd.DataFrame(examples)
    logger.info(f"Processed {len(df)} Spanish-Hebrew sentence pairs")
    return df
