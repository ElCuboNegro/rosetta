"""Nodes for combining bridge language data.

This module combines multiple bridge language sources (English, French, German)
into a single dataset for triangulation.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def combine_bridge_data(english_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare bridge language data (English only).

    Processes English Wiktionary data for use as a bridge dataset.
    Removes duplicates while preserving all unique translation pairs.

    Args:
        english_df: English Wiktionary bridge data.

    Returns:
        Bridge dataset with deduplicated entries.
    """
    logger.info("Processing bridge language data (English)...")
    logger.info(f"Input: {len(english_df)} English entries")

    # Add source column to track origin
    english_df = english_df.copy()
    english_df["bridge_source"] = "en"

    # Use just the English dataframe
    combined_df = english_df

    # Ensure required columns exist (handle empty inputs)
    for col in ["source_lang", "word", "pos"]:
        if col not in combined_df.columns:
            combined_df[col] = pd.Series(dtype=object)

    # Remove exact duplicates (same word, source_lang, and translations)
    before_dedup = len(combined_df)
    combined_df = combined_df.drop_duplicates(subset=["source_lang", "word", "pos"], keep="first")
    after_dedup = len(combined_df)

    logger.info(f"Processed {before_dedup} total entries, {after_dedup} after deduplication")
    logger.info(f"Removed {before_dedup - after_dedup} duplicate entries")

    # Log statistics
    es_count = len(combined_df[combined_df["source_lang"] == "es"])
    he_count = len(combined_df[combined_df["source_lang"] == "he"])

    logger.info(f"Final bridge data: {es_count} Spanish entries, {he_count} Hebrew entries")

    return combined_df
