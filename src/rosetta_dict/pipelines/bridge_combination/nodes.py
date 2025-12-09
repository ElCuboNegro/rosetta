"""Nodes for combining bridge language data.

This module combines multiple bridge language sources (English, French, German)
into a single dataset for triangulation.
"""

import logging
from typing import List

import pandas as pd

logger = logging.getLogger(__name__)


def combine_bridge_data(
    english_df: pd.DataFrame,
    french_df: pd.DataFrame,
    german_df: pd.DataFrame
) -> pd.DataFrame:
    """Combine bridge language data from multiple sources.

    Merges English, French, and German Wiktionary data into a single
    bridge dataset for robust multi-point triangulation. Removes duplicates
    while preserving all unique translation pairs.

    Args:
        english_df: English Wiktionary bridge data.
        french_df: French Wiktionary bridge data.
        german_df: German Wiktionary bridge data.

    Returns:
        Combined bridge dataset with deduplicated entries.
    """
    logger.info("Combining bridge language data...")
    logger.info(f"Input: {len(english_df)} English, {len(french_df)} French, {len(german_df)} German entries")

    # Add source column to track origin
    english_df = english_df.copy()
    french_df = french_df.copy()
    german_df = german_df.copy()

    english_df["bridge_source"] = "en"
    french_df["bridge_source"] = "fr"
    german_df["bridge_source"] = "de"

    # Combine all dataframes
    combined_df = pd.concat([english_df, french_df, german_df], ignore_index=True)

    # Remove exact duplicates (same word, source_lang, and translations)
    before_dedup = len(combined_df)
    combined_df = combined_df.drop_duplicates(
        subset=["source_lang", "word", "pos"],
        keep="first"
    )
    after_dedup = len(combined_df)

    logger.info(f"Combined {before_dedup} total entries, {after_dedup} after deduplication")
    logger.info(f"Removed {before_dedup - after_dedup} duplicate entries")

    # Log statistics
    es_count = len(combined_df[combined_df['source_lang'] == 'es'])
    he_count = len(combined_df[combined_df['source_lang'] == 'he'])
    
    logger.info(f"Final bridge data: {es_count} Spanish entries, {he_count} Hebrew entries")

    return combined_df
