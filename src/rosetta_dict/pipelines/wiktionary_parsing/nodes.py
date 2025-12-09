"""Nodes for parsing Wiktionary JSONL data into structured DataFrames.

This module parses pre-extracted kaikki.org JSONL files to extract words,
IPA pronunciations, definitions, POS tags, and translations.
"""

import gzip
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd

logger = logging.getLogger(__name__)


def parse_spanish_wiktionary(jsonl_path: str) -> pd.DataFrame:
    """Parse Spanish Wiktionary data from kaikki.org JSONL file.

    Extracts Spanish words with IPA pronunciations, definitions, POS tags,
    and translations (Hebrew, English, French, German) from pre-extracted
    kaikki.org data for triangulation.

    Args:
        jsonl_path: Path to kaikki.org Spanish Wiktionary JSONL.gz file.

    Returns:
        DataFrame with columns: word, pos, ipa, definitions (list),
        translations_he, translations_en, translations_fr, translations_de (lists).

    Raises:
        FileNotFoundError: If JSONL file doesn't exist.
    """
    logger.info(f"Parsing Spanish Wiktionary from kaikki.org data: {jsonl_path}...")

    if not Path(jsonl_path).exists():
        raise FileNotFoundError(f"JSONL file not found: {jsonl_path}")

    # Parse JSONL file (with gzip support)
    entries = _load_jsonl_entries(jsonl_path)
    logger.info(f"Loaded {len(entries)} total entries from kaikki.org data")

    # Extract relevant data
    data = []
    spanish_entries = 0

    for entry in entries:
        # Only process Spanish language entries
        if entry.get("lang_code") != "es":
            continue

        spanish_entries += 1

        word = entry.get("word", "")
        if not word:
            continue

        # Get IPA pronunciation
        ipa = _extract_ipa(entry)

        # Get part of speech
        pos = entry.get("pos", "unknown")

        # Get definitions (senses)
        definitions = _extract_definitions(entry, word)

        # Get all translations (English, French, German, Hebrew for triangulation)
        translations = _extract_translations(entry, ["en", "fr", "de", "he"])

        data.append({
            "word": word,
            "pos": pos,
            "ipa": ipa,
            "definitions": definitions,
            "translations_en": translations.get("en", []),
            "translations_fr": translations.get("fr", []),
            "translations_de": translations.get("de", []),
            "translations_he": translations.get("he", [])
        })

    df = pd.DataFrame(data)
    logger.info(f"Found {spanish_entries} Spanish entries out of {len(entries)} total entries")
    logger.info(f"Kept {len(df)} Spanish entries with data")
    
    if len(df) > 0:
        he_trans_count = df['translations_he'].apply(len).sum()
        logger.info(f"Entries with Hebrew translations: {he_trans_count}")
    
    return df


def parse_hebrew_wiktionary(jsonl_path: str) -> pd.DataFrame:
    """Parse Hebrew Wiktionary data from kaikki.org JSONL file.

    Extracts Hebrew words with IPA pronunciations, definitions, POS tags,
    and translations (Spanish, English, French, German) from pre-extracted
    kaikki.org data for triangulation.

    Args:
        jsonl_path: Path to kaikki.org Hebrew Wiktionary JSONL.gz file.

    Returns:
        DataFrame with columns: word, pos, ipa, definitions (list),
        translations_es, translations_en, translations_fr, translations_de (lists).

    Raises:
        FileNotFoundError: If JSONL file doesn't exist.
    """
    logger.info(f"Parsing Hebrew Wiktionary from kaikki.org data: {jsonl_path}...")

    if not Path(jsonl_path).exists():
        raise FileNotFoundError(f"JSONL file not found: {jsonl_path}")

    # Parse JSONL file (with gzip support)
    entries = _load_jsonl_entries(jsonl_path)
    logger.info(f"Loaded {len(entries)} total entries from kaikki.org data")

    # Extract relevant data
    data = []
    hebrew_entries = 0

    for entry in entries:
        # Only process Hebrew language entries
        if entry.get("lang_code") != "he":
            continue

        hebrew_entries += 1

        word = entry.get("word", "")
        if not word:
            continue

        # Get IPA pronunciation
        ipa = _extract_ipa(entry)

        # Get part of speech
        pos = entry.get("pos", "unknown")

        # Get definitions (senses)
        definitions = _extract_definitions(entry, word)

        # Get all translations (English, French, German, Spanish for triangulation)
        translations = _extract_translations(entry, ["en", "fr", "de", "es"])

        data.append({
            "word": word,
            "pos": pos,
            "ipa": ipa,
            "definitions": definitions,
            "translations_en": translations.get("en", []),
            "translations_fr": translations.get("fr", []),
            "translations_de": translations.get("de", []),
            "translations_es": translations.get("es", [])
        })

    df = pd.DataFrame(data)
    logger.info(f"Found {hebrew_entries} Hebrew entries out of {len(entries)} total entries")
    logger.info(f"Kept {len(df)} Hebrew entries with data")
    
    if len(df) > 0:
        es_trans_count = df['translations_es'].apply(len).sum()
        logger.info(f"Entries with Spanish translations: {es_trans_count}")
    
    return df


def parse_english_wiktionary(jsonl_path: str) -> pd.DataFrame:
    """Parse English Wiktionary for Spanish and Hebrew entries with translations.

    English Wiktionary is the richest source for translations between languages.
    This extracts both Spanish and Hebrew word entries that have translations
    to use as bridge data for triangulation.

    Args:
        jsonl_path: Path to kaikki.org English Wiktionary JSONL.gz file.

    Returns:
        DataFrame with Spanish and Hebrew entries with cross-translations.

    Raises:
        FileNotFoundError: If JSONL file doesn't exist.
    """
    logger.info(f"Parsing English Wiktionary for bridge translations: {jsonl_path}...")

    if not Path(jsonl_path).exists():
        raise FileNotFoundError(f"JSONL file not found: {jsonl_path}")

    entries = []
    entry_count = 0

    is_gzipped = jsonl_path.endswith('.gz')
    open_func = gzip.open if is_gzipped else open

    with open_func(jsonl_path, 'rt', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue

            try:
                entry = json.loads(line)

                # Only keep Spanish or Hebrew entries with translations
                lang_code = entry.get("lang_code")
                if lang_code in ["es", "he"] and entry.get("translations"):
                    entries.append(entry)

                entry_count += 1
                if entry_count % 50000 == 0:
                    logger.info(f"Scanned {entry_count} English Wiktionary entries...")

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON on line {line_num}: {e}")
                continue

    logger.info(f"Scanned {entry_count} total English Wiktionary entries")
    logger.info(f"Found {len(entries)} Spanish/Hebrew entries with translations")

    # Extract bridge translation data
    data = []
    for entry in entries:
        word = entry.get("word", "")
        if not word:
            continue

        lang_code = entry.get("lang_code")
        ipa = _extract_ipa(entry)
        pos = entry.get("pos", "unknown")
        definitions = _extract_definitions(entry, word)

        # Get translations to Spanish and Hebrew (English Wiktionary uses "code" field)
        translations_es = []
        translations_he = []
        translations = entry.get("translations", [])
        for trans in translations:
            trans_lang = trans.get("code")  # English Wiktionary uses "code"
            trans_word = trans.get("word", "")
            if not trans_word:
                continue

            if trans_lang == "es" and trans_word not in translations_es:
                translations_es.append(trans_word)
            elif trans_lang == "he" and trans_word not in translations_he:
                translations_he.append(trans_word)

        data.append({
            "source_lang": lang_code,
            "word": word,
            "pos": pos,
            "ipa": ipa,
            "definitions": definitions,
            "translations_es": translations_es,
            "translations_he": translations_he
        })

    df = pd.DataFrame(data)
    logger.info(f"Extracted {len(df)} bridge entries from English Wiktionary")
    
    if len(df) > 0:
        es_count = len(df[df['source_lang'] == 'es'])
        he_count = len(df[df['source_lang'] == 'he'])
        logger.info(f"Spanish entries: {es_count}, Hebrew entries: {he_count}")
    
    return df


def parse_french_wiktionary(jsonl_path: str) -> pd.DataFrame:
    """Parse French Wiktionary for Spanish and Hebrew entries with translations.

    French Wiktionary provides additional bridge data for triangulation.
    This extracts both Spanish and Hebrew word entries that have translations.

    Args:
        jsonl_path: Path to kaikki.org French Wiktionary JSONL.gz file.

    Returns:
        DataFrame with Spanish and Hebrew entries with cross-translations.

    Raises:
        FileNotFoundError: If JSONL file doesn't exist.
    """
    return _parse_bridge_wiktionary(jsonl_path, "French")


def parse_german_wiktionary(jsonl_path: str) -> pd.DataFrame:
    """Parse German Wiktionary for Spanish and Hebrew entries with translations.

    German Wiktionary provides additional bridge data for triangulation.
    This extracts both Spanish and Hebrew word entries that have translations.

    Args:
        jsonl_path: Path to kaikki.org German Wiktionary JSONL.gz file.

    Returns:
        DataFrame with Spanish and Hebrew entries with cross-translations.

    Raises:
        FileNotFoundError: If JSONL file doesn't exist.
    """
    return _parse_bridge_wiktionary(jsonl_path, "German")


def _parse_bridge_wiktionary(jsonl_path: str, language_name: str) -> pd.DataFrame:
    """Parse a bridge language Wiktionary for Spanish/Hebrew entries.

    Args:
        jsonl_path: Path to kaikki.org Wiktionary JSONL.gz file.
        language_name: Name of the language for logging (e.g., "French", "German").

    Returns:
        DataFrame with Spanish and Hebrew entries with cross-translations.
    """
    logger.info(f"Parsing {language_name} Wiktionary for bridge translations: {jsonl_path}...")

    if not Path(jsonl_path).exists():
        raise FileNotFoundError(f"JSONL file not found: {jsonl_path}")

    entries = []
    entry_count = 0

    is_gzipped = jsonl_path.endswith('.gz')
    open_func = gzip.open if is_gzipped else open

    with open_func(jsonl_path, 'rt', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue

            try:
                entry = json.loads(line)

                # Only keep Spanish or Hebrew entries with translations
                lang_code = entry.get("lang_code")
                if lang_code in ["es", "he"] and entry.get("translations"):
                    entries.append(entry)

                entry_count += 1
                if entry_count % 50000 == 0:
                    logger.info(f"Scanned {entry_count} {language_name} Wiktionary entries...")

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON on line {line_num}: {e}")
                continue

    logger.info(f"Scanned {entry_count} total {language_name} Wiktionary entries")
    logger.info(f"Found {len(entries)} Spanish/Hebrew entries with translations")

    # Extract bridge translation data
    data = []
    for entry in entries:
        word = entry.get("word", "")
        if not word:
            continue

        lang_code = entry.get("lang_code")
        ipa = _extract_ipa(entry)
        pos = entry.get("pos", "unknown")
        definitions = _extract_definitions(entry, word)

        # Get translations to Spanish and Hebrew
        translations_es = []
        translations_he = []
        translations = entry.get("translations", [])
        for trans in translations:
            trans_lang = trans.get("lang_code")  # Most Wiktionaries use "lang_code"
            trans_word = trans.get("word", "")
            if not trans_word:
                continue

            if trans_lang == "es" and trans_word not in translations_es:
                translations_es.append(trans_word)
            elif trans_lang == "he" and trans_word not in translations_he:
                translations_he.append(trans_word)

        data.append({
            "source_lang": lang_code,
            "word": word,
            "pos": pos,
            "ipa": ipa,
            "definitions": definitions,
            "translations_es": translations_es,
            "translations_he": translations_he
        })

    df = pd.DataFrame(data)
    logger.info(f"Extracted {len(df)} bridge entries from {language_name} Wiktionary")
    
    if len(df) > 0:
        es_count = len(df[df['source_lang'] == 'es'])
        he_count = len(df[df['source_lang'] == 'he'])
        logger.info(f"Spanish entries: {es_count}, Hebrew entries: {he_count}")
    
    return df


# Helper functions

def _load_jsonl_entries(jsonl_path: str) -> List[Dict[str, Any]]:
    """Load all entries from a JSONL file (supports gzip).

    Args:
        jsonl_path: Path to JSONL or JSONL.gz file.

    Returns:
        List of parsed JSON entries.
    """
    entries = []
    entry_count = 0

    is_gzipped = jsonl_path.endswith('.gz')
    open_func = gzip.open if is_gzipped else open

    with open_func(jsonl_path, 'rt', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue

            try:
                entry = json.loads(line)
                entries.append(entry)
                entry_count += 1

                # Log progress every 5000 entries
                if entry_count % 5000 == 0:
                    logger.info(f"Parsed {entry_count} entries so far...")

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON on line {line_num}: {e}")
                continue

    return entries


def _extract_ipa(entry: Dict[str, Any]) -> str:
    """Extract IPA pronunciation from entry.

    Args:
        entry: Wiktionary entry dictionary.

    Returns:
        IPA string, or empty string if not found.
    """
    sounds = entry.get("sounds", [])
    for sound in sounds:
        if "ipa" in sound:
            return sound["ipa"]
    return ""


def _extract_definitions(entry: Dict[str, Any], word: str) -> List[str]:
    """Extract definitions from entry.

    Args:
        entry: Wiktionary entry dictionary.
        word: The word itself (used as fallback if no definitions).

    Returns:
        List of definition strings.
    """
    definitions = []
    senses = entry.get("senses", [])
    for sense in senses:
        glosses = sense.get("glosses", [])
        if glosses:
            definitions.append(glosses[0])

    # Use word as its own definition if no gloss available
    if not definitions:
        definitions = [word]

    return definitions


def _extract_translations(entry: Dict[str, Any], lang_codes: List[str]) -> Dict[str, List[str]]:
    """Extract translations for specified language codes.

    Args:
        entry: Wiktionary entry dictionary.
        lang_codes: List of language codes to extract (e.g., ["en", "fr", "he"]).

    Returns:
        Dictionary mapping language codes to lists of translations.
    """
    result = {code: [] for code in lang_codes}
    
    translations = entry.get("translations", [])
    for trans in translations:
        lang_code = trans.get("lang_code")  # Most Wiktionaries use "lang_code"
        trans_word = trans.get("word", "")
        
        if not trans_word or lang_code not in lang_codes:
            continue

        if trans_word not in result[lang_code]:
            result[lang_code].append(trans_word)

    return result
