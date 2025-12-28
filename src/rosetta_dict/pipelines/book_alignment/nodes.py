import logging
import re
from pathlib import Path
from typing import List, Dict, Tuple
import pandas as pd
import spacy
import torch
from sentence_transformers import SentenceTransformer, util

logger = logging.getLogger(__name__)


def _segment_sentences_es(text: str) -> List[str]:
    """Segment Spanish text using Spacy."""
    try:
        nlp = spacy.load("es_core_news_sm", disable=["ner", "tagger", "parser", "lemmatizer"])
        nlp.enable_pipe("senter")
    except:
        nlp = spacy.blank("es")
        nlp.add_pipe("sentencizer")

    doc = nlp(text[:1000000])  # Limit for memory safety per book chunk
    return [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 10]


def _segment_sentences_he(text: str) -> List[str]:
    """Segment Hebrew text using simple heuristics (Spacy HE models are large/less common)."""
    # Split by . ! ? followed by space or end of line
    sentences = re.split(r"[.!?]+\s+", text)
    return [s.strip() for s in sentences if len(s.strip()) > 5]


def align_books(gutenberg_files: List[str]) -> pd.DataFrame:
    """
    Ingest and align books from the Gutenberg download list using Semantic Title Matching.

    Args:
        gutenberg_files: List of file paths to downloaded books.

    Returns:
        DataFrame with aligned sentence pairs ['source_es', 'target_he', 'similarity', 'source_book', 'target_book'].
    """
    # Organize by language
    es_files = [f for f in gutenberg_files if "\\es\\" in f or "/es/" in f or "_es_" in f]
    he_files = [f for f in gutenberg_files if "\\he\\" in f or "/he/" in f or "_he_" in f]

    logger.info(
        f"Scanning for alignments among {len(es_files)} Spanish and {len(he_files)} Hebrew books."
    )

    if not es_files or not he_files:
        logger.warning("Insufficient data to perform alignment.")
        return pd.DataFrame(
            columns=["source_es", "target_he", "similarity", "source_book", "target_book"]
        )

    # Load Model (LaBSE is standard for bitext mining and cross-lingual similarity)
    model_name = "sentence-transformers/LaBSE"
    logger.info(f"Loading alignment model: {model_name}")
    model = SentenceTransformer(model_name)

    # --- Step 1: Semantic Title Matching ---
    logger.info("Performing Semantic Title Matching...")

    def extract_title(filepath):
        # Filename: "{id}_{title}.txt" -> "title"
        name = Path(filepath).stem
        parts = name.split("_", 1)
        title = parts[1] if len(parts) > 1 else name
        return title.replace("-", " ").replace("_", " ")

    es_titles = [extract_title(f) for f in es_files]
    he_titles = [extract_title(f) for f in he_files]

    # Embed titles
    es_title_embeddings = model.encode(es_titles, convert_to_tensor=True)
    he_title_embeddings = model.encode(he_titles, convert_to_tensor=True)

    # Compute pairwise similarity
    # util.cos_sim returns query x corpus matrix
    cosine_scores = util.cos_sim(es_title_embeddings, he_title_embeddings)

    matched_pairs = []

    # Threshold for title matching (titles are short, so high semantic overlap is expected for translations)
    TITLE_SIMILARITY_THRESHOLD = 0.70

    # Find best matches
    # Iterate over ES titles and find best HE match
    for i, es_title in enumerate(es_titles):
        best_score_idx = torch.argmax(cosine_scores[i]).item()
        best_score = cosine_scores[i][best_score_idx].item()

        if best_score > TITLE_SIMILARITY_THRESHOLD:
            he_title = he_titles[best_score_idx]
            logger.info(
                f"MATCH FOUND: '{es_title}' (ES) <-> '{he_title}' (HE) [Score: {best_score:.4f}]"
            )
            matched_pairs.append((es_files[i], he_files[best_score_idx]))

    if not matched_pairs:
        logger.warning(
            "No book titles matched above threshold. Attempting generic alignment on ALL combinations (Warning: Expensive!) or Aborting."
        )
        # For prototype safety, we abort if titles don't match to avoid N*M explosion.
        # But let's log the top candidate just to see.
        best_overall = torch.max(cosine_scores).item()
        logger.warning(f"Best ignored match score was: {best_overall:.4f}")
        return pd.DataFrame(
            columns=["source_es", "target_he", "similarity", "source_book", "target_book"]
        )

    # --- Step 2: Content Alignment for Matched Pairs ---
    aligned_data = []

    for src_file, tgt_file in matched_pairs:
        src_path = Path(src_file)
        tgt_path = Path(tgt_file)

        logger.info(f"Aligning content: {src_path.name} <-> {tgt_path.name}")

        src_text = src_path.read_text(encoding="utf-8", errors="replace")
        tgt_text = tgt_path.read_text(encoding="utf-8", errors="replace")

        src_sents = _segment_sentences_es(src_text)
        tgt_sents = _segment_sentences_he(tgt_text)

        logger.info(f"Sentences: {len(src_sents)} (ES) x {len(tgt_sents)} (HE)")

        # Compute Sentence Embeddings
        src_emb = model.encode(
            src_sents, batch_size=32, show_progress_bar=False, convert_to_tensor=True
        )
        tgt_emb = model.encode(
            tgt_sents, batch_size=32, show_progress_bar=False, convert_to_tensor=True
        )

        # Mine bitext
        # We use a stricter threshold for sentences
        hits = util.semantic_search(src_emb, tgt_emb, top_k=1)

        for i, hit in enumerate(hits):
            if not hit:
                continue
            best_hit = hit[0]
            score = best_hit["score"]
            tgt_idx = best_hit["corpus_id"]

            if score > 0.75:  # LaBSE threshold for strong bitext
                aligned_data.append(
                    {
                        "source_es": src_sents[i],
                        "target_he": tgt_sents[tgt_idx],
                        "similarity": score,
                        "source_book": src_path.name,
                        "target_book": tgt_path.name,
                    }
                )

    logger.info(f"Total aligned sentences generated: {len(aligned_data)}")
    return pd.DataFrame(aligned_data)
