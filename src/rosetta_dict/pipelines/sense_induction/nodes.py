import logging
import re
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
import torch
from sklearn.cluster import KMeans
from sklearn.metrics import davies_bouldin_score, silhouette_score
from transformers import BertModel, BertTokenizer

from rosetta_dict.utils.word_extraction import (
    build_word_index,
    extract_lemmas_from_sentence,
    get_sentences_for_word,
)

try:
    import hdbscan

    HDBSCAN_AVAILABLE = True
except ImportError:
    HDBSCAN_AVAILABLE = False
    logging.warning("HDBSCAN not available. Install with: pip install hdbscan")

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


def compute_ensemble_embeddings(text_series: pd.Series, target_word_series: pd.Series) -> pd.Series:
    """
    Compute ensemble embeddings using multiple strategies:
    1. Target word contextual embedding
    2. Sentence-level [CLS] embedding
    3. Local context window around target word

    Returns concatenated embeddings for better sense discrimination.
    """
    tokenizer, model = _get_model()
    ensemble_embeddings = []

    for text, target_lemma in zip(text_series, target_word_series):
        if not text or not target_lemma:
            ensemble_embeddings.append(None)
            continue

        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
        with torch.no_grad():
            outputs = model(**inputs)

        last_hidden = outputs.last_hidden_state.squeeze(0)
        input_ids = inputs["input_ids"][0].tolist()
        tokens = tokenizer.convert_ids_to_tokens(input_ids)

        # Strategy 1: Target word embedding
        target_tokens = tokenizer.tokenize(target_lemma)
        target_start = -1
        if target_tokens:
            target_first_token = target_tokens[0]
            for idx, tok in enumerate(tokens):
                if tok == target_first_token or tok == target_lemma:
                    target_start = idx
                    break

        if target_start != -1:
            word_emb = last_hidden[target_start].numpy()
        else:
            word_emb = torch.mean(last_hidden, dim=0).numpy()

        # Strategy 2: [CLS] token (sentence-level context)
        cls_emb = last_hidden[0].numpy()

        # Strategy 3: Local context (3 tokens before and after target)
        if target_start != -1:
            context_start = max(1, target_start - 3)
            context_end = min(len(last_hidden) - 1, target_start + 4)
            context_emb = torch.mean(last_hidden[context_start:context_end], dim=0).numpy()
        else:
            context_emb = torch.mean(last_hidden[1:-1], dim=0).numpy()

        # Concatenate all strategies
        ensemble = np.concatenate([word_emb, cls_emb * 0.5, context_emb * 0.3])
        ensemble_embeddings.append(ensemble)

    return pd.Series(ensemble_embeddings)


def find_optimal_k_elbow(embeddings: np.ndarray, max_k: int = 10) -> Tuple[int, Dict[str, Any]]:
    """
    Find optimal number of clusters using elbow method with silhouette score.

    Returns:
        Tuple of (optimal_k, metrics_dict)
    """
    if len(embeddings) < 2:
        return 1, {"method": "insufficient_data"}

    max_k = min(max_k, len(embeddings) - 1)
    if max_k < 2:
        return 1, {"method": "single_cluster"}

    inertias = []
    silhouette_scores = []
    db_scores = []

    for k in range(2, max_k + 1):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)

        inertias.append(kmeans.inertia_)

        # Silhouette score (higher is better, -1 to 1)
        if len(np.unique(labels)) > 1:
            sil_score = silhouette_score(embeddings, labels)
            silhouette_scores.append(sil_score)

            # Davies-Bouldin score (lower is better)
            db_score = davies_bouldin_score(embeddings, labels)
            db_scores.append(db_score)
        else:
            silhouette_scores.append(-1)
            db_scores.append(float("inf"))

    # Find elbow point in inertia curve
    if len(inertias) > 0:
        # Calculate rate of change
        deltas = np.diff(inertias)
        if len(deltas) > 1:
            delta_deltas = np.diff(deltas)
            # Elbow is where second derivative is maximum
            elbow_k = np.argmax(delta_deltas) + 2  # +2 because we started at k=2
        else:
            elbow_k = 2
    else:
        elbow_k = 2

    # Choose k with best silhouette score (prefer fewer clusters in ties)
    if silhouette_scores:
        best_sil_k = np.argmax(silhouette_scores) + 2

        # If silhouette score difference is small, prefer elbow method
        if (
            len(silhouette_scores) > 1
            and silhouette_scores[best_sil_k - 2] - silhouette_scores[elbow_k - 2] < 0.1
        ):
            optimal_k = elbow_k
        else:
            optimal_k = best_sil_k
    else:
        optimal_k = elbow_k

    metrics = {
        "method": "elbow_silhouette",
        "optimal_k": optimal_k,
        "elbow_k": elbow_k,
        "best_silhouette_k": best_sil_k if silhouette_scores else None,
        "silhouette_scores": silhouette_scores,
        "inertias": inertias,
    }

    return optimal_k, metrics


def cluster_hdbscan(
    embeddings: np.ndarray, min_cluster_size: int = 2
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Perform density-based clustering using HDBSCAN.

    Returns:
        Tuple of (cluster_labels, metadata_dict)
    """
    if not HDBSCAN_AVAILABLE:
        raise ImportError("HDBSCAN not available. Falling back to KMeans.")

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=1,
        metric="euclidean",
        cluster_selection_method="eom",
    )

    labels = clusterer.fit_predict(embeddings)

    # HDBSCAN uses -1 for noise points; we'll keep them separate
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = np.sum(labels == -1)

    metadata = {
        "method": "hdbscan",
        "n_clusters": n_clusters,
        "n_noise_points": n_noise,
        "cluster_persistence": clusterer.cluster_persistence_.tolist()
        if hasattr(clusterer, "cluster_persistence_")
        else None,
    }

    return labels, metadata


def validate_clustering_quality(
    embeddings: np.ndarray, labels: np.ndarray, word: str
) -> Dict[str, Any]:
    """
    Validate clustering quality and detect potential issues.

    Returns dictionary with quality metrics and warnings.
    """
    n_clusters = len(np.unique(labels[labels >= 0]))

    if n_clusters <= 1:
        return {
            "quality_score": 0.0,
            "warnings": ["Only one cluster found"],
            "n_clusters": n_clusters,
        }

    # Silhouette score
    try:
        sil_score = silhouette_score(embeddings, labels)
    except (ValueError, RuntimeError) as e:
        logger.debug(f"Silhouette score calculation failed: {e}")
        sil_score = -1.0

    # Davies-Bouldin score (lower is better)
    try:
        db_score = davies_bouldin_score(embeddings, labels)
    except (ValueError, RuntimeError) as e:
        logger.debug(f"Davies-Bouldin score calculation failed: {e}")
        db_score = float("inf")

    # Check cluster sizes
    unique_labels, counts = np.unique(labels[labels >= 0], return_counts=True)
    min_cluster_size = np.min(counts)
    max_cluster_size = np.max(counts)
    cluster_balance = min_cluster_size / max_cluster_size if max_cluster_size > 0 else 0

    # Generate warnings
    warnings = []
    if sil_score < 0.2:
        warnings.append(f"Low silhouette score ({sil_score:.3f}): clusters may be poorly separated")
    if db_score > 2.0:
        warnings.append(f"High Davies-Bouldin score ({db_score:.3f}): clusters may overlap")
    if cluster_balance < 0.1:
        warnings.append(
            f"Imbalanced clusters: sizes range from {min_cluster_size} to {max_cluster_size}"
        )
    if n_clusters > len(embeddings) / 2:
        warnings.append(f"Too many clusters ({n_clusters}) for {len(embeddings)} examples")

    # Overall quality score (0-1, higher is better)
    quality_score = (sil_score + 1) / 2 * (1 / (1 + db_score / 10))

    return {
        "quality_score": quality_score,
        "silhouette_score": sil_score,
        "davies_bouldin_score": db_score,
        "n_clusters": n_clusters,
        "cluster_sizes": counts.tolist(),
        "cluster_balance": cluster_balance,
        "warnings": warnings,
        "word": word,
    }


def induce_senses(
    wiktionary_examples: pd.DataFrame, book_sentences: pd.DataFrame, parameters: Dict[str, Any]
) -> pd.DataFrame:
    """
    Perform Word Sense Induction on the corpus with improved clustering.
    Combines examples from Wiktionary with relevant sentences from the Book Alignments.

    Args:
        wiktionary_examples: DataFrame with ['source_word', 'example_text', ...].
        book_sentences: DataFrame with ['source_es', 'target_he', 'similarity', ...].
        parameters: clustering parameters including:
            - min_examples: minimum examples needed for clustering
            - max_clusters: maximum clusters to consider
            - clustering_method: 'auto', 'kmeans', or 'hdbscan'
            - use_ensemble_embeddings: whether to use ensemble embeddings
            - quality_threshold: minimum quality score to accept clustering

    Returns:
        DataFrame with added 'sense_cluster_id' and quality metrics.
    """
    logger.info("Starting Improved Sense Induction...")

    results = []
    quality_metrics = []

    # Extract list of target words from BOTH Wiktionary AND Books
    wiktionary_words = set(wiktionary_examples["source_word"].unique())
    logger.info(f"Found {len(wiktionary_words)} words in Wiktionary")

    # Get parameters
    extract_all_words = parameters.get("extract_all_book_words", False)
    max_words_to_process = parameters.get("max_words_to_process", 500)

    if extract_all_words and book_sentences is not None and not book_sentences.empty:
        logger.info("Extracting ALL unique words from book corpus...")

        all_book_words = set()
        for idx, sentence in enumerate(book_sentences["source_es"]):
            if idx % 1000 == 0:
                logger.info(
                    f"Processed {idx}/{len(book_sentences)} sentences, found {len(all_book_words)} unique words"
                )

            lemmas = extract_lemmas_from_sentence(sentence, use_spacy=True)
            all_book_words.update(lemmas)

        logger.info(f"Found {len(all_book_words)} unique words in book corpus")

        # Combine with Wiktionary words
        target_words = list(wiktionary_words | all_book_words)
        logger.info(
            f"Total unique words: {len(target_words)} (Wiktionary: {len(wiktionary_words)}, Books only: {len(all_book_words - wiktionary_words)})"
        )
    else:
        # Only use Wiktionary words (original behavior)
        target_words = list(wiktionary_words)

    # Limit to max_words_to_process
    if len(target_words) > max_words_to_process:
        logger.info(f"Limiting to {max_words_to_process} words (total: {len(target_words)})")
        target_words = target_words[:max_words_to_process]

    logger.info(f"Processing {len(target_words)} words.")

    # Get parameters
    clustering_method = parameters.get("clustering_method", "auto")
    use_ensemble = parameters.get("use_ensemble_embeddings", True)
    quality_threshold = parameters.get("quality_threshold", 0.0)
    use_word_index = parameters.get("use_word_index", True)
    max_book_sentences = parameters.get("max_book_sentences_per_word", 50)

    # Build word index once for efficient lookup (if enabled)
    word_index_df = None
    if use_word_index and book_sentences is not None and not book_sentences.empty:
        logger.info("Building word index for efficient sentence retrieval...")
        word_index_df = build_word_index(book_sentences)
        logger.info(f"Word index built with {len(word_index_df)} entries")

    for word in target_words:
        # 1. Get Wiktionary Examples
        wiki_data = wiktionary_examples[wiktionary_examples["source_word"] == word].copy()
        wiki_data["corpus_source"] = "wiktionary"
        wiki_data["sentence_text"] = wiki_data["example_text"]

        # 2. Find relevant Book Sentences
        if use_word_index and word_index_df is not None:
            # Use pre-built word index for fast lookup
            book_matches = get_sentences_for_word(
                word, word_index_df, max_sentences=max_book_sentences
            )
            if not book_matches.empty:
                book_matches["source_word"] = word
                # Rename columns for consistency
                if (
                    "sentence_text" not in book_matches.columns
                    and "source_es" in book_matches.columns
                ):
                    book_matches["sentence_text"] = book_matches["source_es"]
        else:
            # Fall back to regex search (slower but works without index)
            word_regex = rf"\b{re.escape(word)}\b"
            book_matches = book_sentences[
                book_sentences["source_es"].str.contains(
                    word_regex, regex=True, case=False, na=False
                )
            ].copy()

            if len(book_matches) > max_book_sentences:
                book_matches = book_matches.sample(n=max_book_sentences, random_state=42)

            book_matches["source_word"] = word
            book_matches["corpus_source"] = "gutenberg"
            book_matches["sentence_text"] = book_matches["source_es"]

        # Combine and preserve Wiktionary sense information if available
        wiki_cols = ["source_word", "sentence_text", "corpus_source"]
        if "sense" in wiki_data.columns:
            wiki_cols.append("sense")
            wiki_data["wiktionary_sense"] = wiki_data["sense"]

        combined_data = pd.concat(
            [
                wiki_data[wiki_cols],
                book_matches[["source_word", "sentence_text", "corpus_source"]],
            ],
            ignore_index=True,
        )

        if len(combined_data) < parameters.get("min_examples", 5):
            combined_data["sense_cluster_id"] = -1
            combined_data["cluster_quality_score"] = 0.0
            results.append(combined_data)
            continue

        logger.info(f"Inducing senses for '{word}' ({len(combined_data)} total examples)")

        # Compute embeddings (ensemble or standard)
        if use_ensemble:
            embeddings_series = compute_ensemble_embeddings(
                combined_data["sentence_text"], combined_data["source_word"]
            )
        else:
            embeddings_series = compute_embeddings(
                combined_data["sentence_text"], combined_data["source_word"]
            )

        # Filter failures
        valid_mask = embeddings_series.notna()
        valid_embeddings = np.stack(embeddings_series[valid_mask].values)

        if len(valid_embeddings) < 2:
            combined_data["sense_cluster_id"] = -1
            combined_data["cluster_quality_score"] = 0.0
            results.append(combined_data)
            continue

        # Perform clustering based on method
        try:
            if clustering_method == "hdbscan" and HDBSCAN_AVAILABLE:
                clusters, metadata = cluster_hdbscan(valid_embeddings, min_cluster_size=2)
                logger.info(f"HDBSCAN found {metadata['n_clusters']} clusters for '{word}'")

            elif clustering_method == "auto":
                # Try HDBSCAN first, fall back to optimal KMeans
                if HDBSCAN_AVAILABLE and len(valid_embeddings) >= 5:
                    try:
                        clusters, metadata = cluster_hdbscan(valid_embeddings, min_cluster_size=2)
                        # If too many noise points, fall back to KMeans
                        if metadata["n_noise_points"] > len(valid_embeddings) * 0.3:
                            raise ValueError("Too many noise points, using KMeans")
                    except Exception as e:
                        logger.info(f"HDBSCAN failed for '{word}': {e}, using KMeans")
                        optimal_k, k_metrics = find_optimal_k_elbow(
                            valid_embeddings, max_k=parameters.get("max_clusters", 10)
                        )
                        kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
                        clusters = kmeans.fit_predict(valid_embeddings)
                        metadata = k_metrics
                else:
                    # Use KMeans with optimal k selection
                    optimal_k, k_metrics = find_optimal_k_elbow(
                        valid_embeddings, max_k=parameters.get("max_clusters", 10)
                    )
                    kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
                    clusters = kmeans.fit_predict(valid_embeddings)
                    metadata = k_metrics
                    logger.info(
                        f"Optimal k={optimal_k} for '{word}' (method: {metadata.get('method', 'kmeans')})"
                    )

            else:
                # Standard KMeans with optimal k
                optimal_k, k_metrics = find_optimal_k_elbow(
                    valid_embeddings, max_k=parameters.get("max_clusters", 10)
                )
                kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
                clusters = kmeans.fit_predict(valid_embeddings)
                metadata = k_metrics

            # Validate clustering quality
            quality = validate_clustering_quality(valid_embeddings, clusters, word)
            quality_metrics.append(quality)

            # Log warnings if any
            if quality["warnings"]:
                logger.warning(f"Quality issues for '{word}': {'; '.join(quality['warnings'])}")

            # Store results
            combined_data.loc[valid_mask, "sense_cluster_id"] = clusters
            combined_data["cluster_quality_score"] = quality["quality_score"]
            combined_data["clustering_method"] = metadata.get("method", "unknown")

            # If quality is too low, mark as uncertain
            if quality["quality_score"] < quality_threshold:
                logger.warning(
                    f"Low quality clustering for '{word}' "
                    f"(score: {quality['quality_score']:.3f}). Consider manual review."
                )

        except Exception as e:
            logger.error(f"Clustering failed for '{word}': {e}")
            combined_data["sense_cluster_id"] = -1
            combined_data["cluster_quality_score"] = 0.0
            combined_data["clustering_method"] = "failed"

        results.append(combined_data)

    if not results:
        return pd.DataFrame()

    final_df = pd.concat(results, ignore_index=True)

    # Log overall quality statistics
    if quality_metrics:
        avg_quality = np.mean([q["quality_score"] for q in quality_metrics])
        logger.info(f"Average clustering quality: {avg_quality:.3f}")
        logger.info(f"Total words processed: {len(quality_metrics)}")

    return final_df
