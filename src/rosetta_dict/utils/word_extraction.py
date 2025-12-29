"""
Utilities for extracting and indexing words from book sentences.
"""
import logging
import re
from collections import defaultdict
from typing import Dict, List, Set

import pandas as pd
import spacy

logger = logging.getLogger(__name__)

# Global spacy model cache
_nlp_es = None


def _get_spacy_model():
    """Get or load Spanish spacy model."""
    global _nlp_es
    if _nlp_es is None:
        try:
            _nlp_es = spacy.load("es_core_news_sm", disable=["ner", "parser"])
            logger.info("Loaded Spanish spacy model for lemmatization")
        except OSError:
            logger.warning("Spanish spacy model not found, using simple tokenization")
            _nlp_es = None
    return _nlp_es


def extract_lemmas_from_sentence(sentence: str, use_spacy: bool = True) -> List[str]:
    """
    Extract lemmatized words from a Spanish sentence.

    Args:
        sentence: Spanish sentence text
        use_spacy: Whether to use spacy for lemmatization (vs simple lowercasing)

    Returns:
        List of lemmatized words
    """
    if not sentence or not isinstance(sentence, str):
        return []

    nlp = _get_spacy_model() if use_spacy else None

    if nlp:
        doc = nlp(sentence[:1000])  # Limit sentence length
        lemmas = [
            token.lemma_.lower()
            for token in doc
            if token.is_alpha and len(token.lemma_) > 2 and not token.is_stop
        ]
    else:
        # Fallback: simple word extraction
        words = re.findall(r'\b[a-záéíóúñü]+\b', sentence.lower())
        lemmas = [w for w in words if len(w) > 2]

    return lemmas


def build_word_index(book_sentences_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build an inverted index mapping each word to all sentences containing it.

    Args:
        book_sentences_df: DataFrame with 'source_es' column containing Spanish sentences

    Returns:
        DataFrame with columns:
            - lemma: the lemmatized word
            - sentence_text: the sentence containing the word
            - source_book: book source
            - target_he: Hebrew translation (if available)
            - similarity: alignment score (if available)
            - corpus_source: always 'gutenberg'
    """
    logger.info(f"Building word index from {len(book_sentences_df)} sentences...")

    # Build inverted index: word -> list of sentence indices
    word_to_indices: Dict[str, Set[int]] = defaultdict(set)

    for idx, row in book_sentences_df.iterrows():
        sentence = row.get('source_es', '')
        if not sentence:
            continue

        lemmas = extract_lemmas_from_sentence(sentence)
        for lemma in lemmas:
            word_to_indices[lemma].add(idx)

    logger.info(f"Found {len(word_to_indices)} unique words in corpus")

    # Create expanded DataFrame with one row per (word, sentence) pair
    records = []
    for lemma, indices in word_to_indices.items():
        for idx in indices:
            row = book_sentences_df.loc[idx]
            records.append({
                'lemma': lemma,
                'sentence_text': row.get('source_es', ''),
                'source_book': row.get('source_book', ''),
                'target_he': row.get('target_he', ''),
                'similarity': row.get('similarity', 0.0),
                'corpus_source': 'gutenberg',
            })

    indexed_df = pd.DataFrame(records)
    logger.info(f"Created word index with {len(indexed_df)} (word, sentence) pairs")

    return indexed_df


def get_sentences_for_word(
    word: str,
    word_index_df: pd.DataFrame,
    max_sentences: int = 100
) -> pd.DataFrame:
    """
    Retrieve all sentences containing a specific word from the pre-built index.

    Args:
        word: The lemmatized word to search for
        word_index_df: Pre-built word index from build_word_index()
        max_sentences: Maximum number of sentences to return

    Returns:
        DataFrame with sentences containing the word
    """
    matches = word_index_df[word_index_df['lemma'] == word.lower()]

    if len(matches) > max_sentences:
        # Sample diverse sentences if too many
        matches = matches.sample(n=max_sentences, random_state=42)

    return matches.drop(columns=['lemma'])  # Remove lemma column for consistency
