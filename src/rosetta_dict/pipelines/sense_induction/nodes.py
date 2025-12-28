import logging
import re
from typing import List, Dict, Any
import pandas as pd
import numpy as np
from transformers import BertTokenizer, BertModel
from sklearn.cluster import KMeans
import torch

logger = logging.getLogger(__name__)

# Global model cache to avoid reloading
MODEL_NAME = "dccuchile/bert-base-spanish-wwm-cased"
_tokenizer = None
_model = None


def _get_model():
    global _tokenizer, _model
    if _model is None:
        logger.info(f"Loading BERT model: {MODEL_NAME}")
        _tokenizer = BertTokenizer.from_pretrained(MODEL_NAME)
        _model = BertModel.from_pretrained(MODEL_NAME)
        _model.eval()
    return _tokenizer, _model


def compute_embeddings(text_series: pd.Series, target_word_series: pd.Series) -> pd.Series:
    """
    Compute contextual embeddings for the target word in each sentence.

    Args:
        text_series: Series of sentences.
        target_word_series: Series of target lemmas to focus on.

    Returns:
        Series of numpy arrays (embeddings).
    """
    tokenizer, model = _get_model()
    embeddings = []

    # Process in small batches or single items (for simplicity/prototype)
    # Ideally batch process for speed, but word alignment indices are tricky in batches.

    for text, target_lemma in zip(text_series, target_word_series):
        if not text or not target_lemma:
            embeddings.append(None)
            continue

        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
        with torch.no_grad():
            outputs = model(**inputs)

        # Strategy: Mean pooling of all tokens matching the target word?
        # Or just [CLS]? Method says "Contextual Embeddings for target lemmas".
        # We need to find the token indices for the target word.

        # Naive token matching
        target_tokens = tokenizer.tokenize(target_lemma)
        if not target_tokens:
            embeddings.append(np.zeros(768))  # Fallback
            continue

        # Find where target tokens appear in the input
        # detailed matching logic is complex, for prototype/MVP we will use:
        # **Sentence Embedding** ([CLS]) as a proxy for specific sense in context?
        # NO, "bank" in "I sat on the bank" vs "I went to the bank".
        # [CLS] captures the whole sentence meaning, which *includes* the word sense.
        # This is often 'good enough' for WSI.

        # Better: Average of all token embeddings (last hidden state).
        last_hidden = outputs.last_hidden_state.squeeze(0)  # [Seq_Len, 768]
        # sentence_emb = torch.mean(last_hidden, dim=0).numpy()

        # Even Better: Try to find the word.
        input_ids = inputs["input_ids"][0].tolist()
        tokens = tokenizer.convert_ids_to_tokens(input_ids)

        # Simple string match for first token of target
        target_start = -1
        target_first_token = target_tokens[0]  # e.g. "banco" -> "ban" or "banco"

        for idx, tok in enumerate(tokens):
            if tok == target_first_token or tok == target_lemma:  # Exact or subword match
                target_start = idx
                break

        if target_start != -1:
            # Use specific word embedding
            word_emb = last_hidden[target_start].numpy()
            embeddings.append(word_emb)
        else:
            # Fallback to mean pooling of sentence if word not found (tokenization mismatch)
            embeddings.append(torch.mean(last_hidden, dim=0).numpy())

    return pd.Series(embeddings)


def induce_senses(
    wiktionary_examples: pd.DataFrame, book_sentences: pd.DataFrame, parameters: Dict[str, Any]
) -> pd.DataFrame:
    """
    Perform Word Sense Induction on the corpus.
    Combines examples from Wiktionary with relevant sentences from the Book Alignments.

    Args:
        wiktionary_examples: DataFrame with ['source_word', 'example_text', ...].
        book_sentences: DataFrame with ['source_es', 'target_he', 'similarity', ...].
        parameters: clustering parameters.

    Returns:
        DataFrame with added 'sense_cluster_id'.
    """
    logger.info("Starting Sense Induction...")

    results = []

    # Pre-filter books data to save time?
    # No, we iterate target words.

    # Extract list of target words from Wiktionary data
    # (Only process words that have examples)
    target_words = wiktionary_examples["source_word"].unique()

    # Process first 500 words with examples for verification
    target_words = target_words[:500]
    logger.info(f"Processing {len(target_words)} words.")

    # Create simple search index for books (Naive)
    # Ideally, we'd use a full text index or inverted index.
    # For MVP, we'll scan.

    for word in target_words:
        # 1. Get Wiktionary Examples
        wiki_data = wiktionary_examples[wiktionary_examples["source_word"] == word].copy()
        wiki_data["corpus_source"] = "wiktionary"
        wiki_data["sentence_text"] = wiki_data["example_text"]

        # 2. Find relevant Book Sentences
        # Simple string containment
        # " banco " (spaces) to avoid "atrabancar"
        # Regex is safer: \bword\b
        word_regex = rf"\b{re.escape(word)}\b"
        book_matches = book_sentences[
            book_sentences["source_es"].str.contains(word_regex, regex=True, case=False, na=False)
        ].copy()

        book_matches["source_word"] = word
        book_matches["corpus_source"] = "gutenberg"
        book_matches["sentence_text"] = book_matches["source_es"]

        # Combine
        # Select consistent columns
        combined_data = pd.concat(
            [
                wiki_data[["source_word", "sentence_text", "corpus_source"]],
                book_matches[["source_word", "sentence_text", "corpus_source"]],
            ],
            ignore_index=True,
        )

        if len(combined_data) < parameters.get("min_examples", 5):
            # Not enough data for WSI
            combined_data["sense_cluster_id"] = -1
            results.append(combined_data)
            continue

        logger.info(f"Inducing senses for '{word}' ({len(combined_data)} total examples)")

        # Compute embeddings
        # Note: We need to pass the target WORD to the embedding function
        # so it knows what to look for in the sentence.
        embeddings_series = compute_embeddings(
            combined_data["sentence_text"], combined_data["source_word"]
        )

        # Filter failures
        valid_mask = embeddings_series.notna()
        valid_embeddings = np.stack(embeddings_series[valid_mask].values)

        if len(valid_embeddings) < 2:
            combined_data["sense_cluster_id"] = -1
            results.append(combined_data)
            continue

        # Clustering
        n_clusters = parameters.get("max_clusters", 3)
        kmeans = KMeans(
            n_clusters=min(len(valid_embeddings), n_clusters), random_state=42, n_init="auto"
        )
        clusters = kmeans.fit_predict(valid_embeddings)

        combined_data.loc[valid_mask, "sense_cluster_id"] = clusters
        results.append(combined_data)

    if not results:
        return pd.DataFrame()

    return pd.concat(results, ignore_index=True)
