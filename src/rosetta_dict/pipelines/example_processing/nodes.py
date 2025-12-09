"""Nodes for processing Tatoeba sentence examples.

This module provides functions for processing Spanish-Hebrew sentence pairs
from the Tatoeba corpus.
"""

import logging
from typing import List

import pandas as pd

logger = logging.getLogger(__name__)


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
        es_words = _tokenize_spanish(es_text)
        he_words = _tokenize_hebrew(he_text)

        examples.append({
            "es": es_text,
            "he": he_text,
            "es_words": es_words,
            "he_words": he_words
        })

    df = pd.DataFrame(examples)
    logger.info(f"Processed {len(df)} Spanish-Hebrew sentence pairs")
    return df


def _tokenize_spanish(text: str) -> List[str]:
    """Tokenize Spanish text into words.

    Args:
        text: Spanish text to tokenize.

    Returns:
        List of lowercase Spanish words (length > 2).
    """
    return [
        w.strip('.,!?;:()[]"\'').lower()
        for w in text.split()
        if len(w) > 2
    ]


def _tokenize_hebrew(text: str) -> List[str]:
    """Tokenize Hebrew text into words.

    Args:
        text: Hebrew text to tokenize.

    Returns:
        List of Hebrew words (length > 1).
    """
    return [
        w.strip('.,!?;:()[]"\'')
        for w in text.split()
        if len(w) > 1
    ]
