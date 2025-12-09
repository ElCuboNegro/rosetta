"""Nodes for filtering and cleaning word entries.

This module provides functions for removing unwanted entries like proper nouns.
"""

import logging
from typing import Set

import pandas as pd

logger = logging.getLogger(__name__)

# POS tags that indicate proper nouns
PROPER_NOUN_TAGS: Set[str] = {"name", "proper noun", "propn", "proper_noun"}

# Common abbreviations that should not be filtered
COMMON_ABBREVIATIONS: Set[str] = {
    "ISBN", "USA", "UK", "TV", "PC", "CD", "DVD", "GPS", "SMS",
    "HTTP", "HTML", "CSS", "PDF", "API", "URL", "USB", "RAM"
}


def filter_proper_nouns(df: pd.DataFrame, column_name: str = "word") -> pd.DataFrame:
    """Filter out proper nouns (names, places) from word entries.

    Uses POS tags and capitalization heuristics to identify proper nouns.

    Args:
        df: DataFrame with word entries.
        column_name: Column containing the word text.

    Returns:
        DataFrame with proper nouns removed.
    """
    logger.info(f"Filtering proper nouns from {len(df)} entries...")

    # Filter by POS tag
    if "pos" in df.columns:
        df_filtered = df[~df["pos"].str.lower().isin(PROPER_NOUN_TAGS)].copy()
        removed = len(df) - len(df_filtered)
        logger.info(f"Removed {removed} entries with proper noun POS tags")
    else:
        df_filtered = df.copy()

    # Additional heuristic: remove entries where word starts with capital letter
    before_cap_filter = len(df_filtered)
    df_filtered = df_filtered[~df_filtered[column_name].apply(_is_likely_proper_noun)].copy()
    cap_removed = before_cap_filter - len(df_filtered)

    logger.info(f"Removed {cap_removed} additional entries with capitalization")
    logger.info(f"Total kept: {len(df_filtered)} / {len(df)} ({100*len(df_filtered)/len(df):.1f}%)")

    return df_filtered


def _is_likely_proper_noun(word: str) -> bool:
    """Check if a word is likely a proper noun based on capitalization.

    Args:
        word: Word to check.

    Returns:
        True if likely a proper noun, False otherwise.
    """
    if not isinstance(word, str) or not word:
        return False
    
    # Skip if it's a common abbreviation
    if word in COMMON_ABBREVIATIONS:
        return False
    
    # Check if first letter is uppercase
    return word[0].isupper()
