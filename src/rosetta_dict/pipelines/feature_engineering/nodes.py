"""Nodes for computing features from word entries.

This module provides functions for adding frequency ranks and other
computed features to dictionary entries.
"""

import logging
from typing import Tuple

import pandas as pd

logger = logging.getLogger(__name__)


def add_frequency_ranks(
    spanish_df: pd.DataFrame,
    hebrew_df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Add frequency ranks to word entries based on occurrence patterns.

    Uses multiple signals to estimate word frequency:
    - Number of senses (polysemy indicates common words)
    - Number of translations available
    - Word length (shorter words tend to be more common)

    Args:
        spanish_df: Spanish entries.
        hebrew_df: Hebrew entries.

    Returns:
        Tuple of (spanish_df, hebrew_df) with frequency_rank column added.
    """
    logger.info("Computing frequency ranks...")

    # Compute scores
    spanish_df = spanish_df.copy()
    hebrew_df = hebrew_df.copy()

    spanish_df["frequency_score"] = spanish_df.apply(_compute_frequency_score, axis=1)
    hebrew_df["frequency_score"] = hebrew_df.apply(_compute_frequency_score, axis=1)

    # Convert to ranks (1 = most common)
    spanish_df["frequency_rank"] = spanish_df["frequency_score"].rank(
        ascending=False, method="dense"
    ).astype(int)
    hebrew_df["frequency_rank"] = hebrew_df["frequency_score"].rank(
        ascending=False, method="dense"
    ).astype(int)

    logger.info(
        f"Assigned frequency ranks: Spanish (1-{spanish_df['frequency_rank'].max()}), "
        f"Hebrew (1-{hebrew_df['frequency_rank'].max()})"
    )

    return spanish_df, hebrew_df


def _compute_frequency_score(row: pd.Series) -> float:
    """Compute frequency score for a word entry.

    Args:
        row: DataFrame row with word entry data.

    Returns:
        Frequency score (higher = more common).
    """
    score = 0.0

    # More translations = more common word (weight: 40%)
    if "translations_he" in row and isinstance(row["translations_he"], list):
        score += len(row["translations_he"]) * 0.4
    if "translations_es" in row and isinstance(row["translations_es"], list):
        score += len(row["translations_es"]) * 0.4
    if "translations_en" in row and isinstance(row["translations_en"], list):
        score += len(row["translations_en"]) * 0.2
    if "translations_fr" in row and isinstance(row["translations_fr"], list):
        score += len(row["translations_fr"]) * 0.1

    # More definitions = more polysemic = more common (weight: 30%)
    if "definitions" in row and isinstance(row["definitions"], list):
        score += len(row["definitions"]) * 0.3

    # Shorter words tend to be more frequent (weight: 30%)
    if "word" in row and isinstance(row["word"], str):
        word_len = len(row["word"])
        # Inverse length score: 1-10 chars gets max points, longer gets less
        length_score = max(0, (10 - word_len) / 10) * 0.3
        score += length_score

    return score
