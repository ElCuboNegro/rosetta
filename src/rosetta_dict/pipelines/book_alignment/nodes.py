import json
import logging
import re
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
import spacy
import torch
from sentence_transformers import SentenceTransformer, util
from tqdm import tqdm

from rosetta_dict.utils.book_validation import BookPairValidator
from rosetta_dict.utils.vector_store import VectorStore

logger = logging.getLogger(__name__)


def _segment_sentences_es(text: str) -> List[str]:
    """Segment Spanish text using Spacy."""
    try:
        nlp = spacy.load("es_core_news_sm", disable=["ner", "tagger", "parser", "lemmatizer"])
        nlp.enable_pipe("senter")
    except Exception:
        nlp = spacy.blank("es")
        nlp.add_pipe("sentencizer")

    doc = nlp(text[:1000000])  # Limit for memory safety per book chunk
    return [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 10]


def _segment_sentences_he(text: str) -> List[str]:
    """Segment Hebrew text with line-joining and smarter heuristics."""
    # 1. Normalize segment: join lines that are probably the same sentence
    # Raw Gutenberg/Ben Yehuda files often have hard-wrapping at ~70 chars
    lines = text.splitlines()
    processed_lines = []
    current_chunk = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_chunk:
                processed_lines.append(" ".join(current_chunk))
                current_chunk = []
            continue

        current_chunk.append(stripped)
        # If line ends with typical sentence ender, it might be a sentence break
        # but we also check length. If it's a short line, it's likely a title/header.
        if re.search(r"[.!?:]$", stripped) and len(stripped) > 40:
            processed_lines.append(" ".join(current_chunk))
            current_chunk = []

    if current_chunk:
        processed_lines.append(" ".join(current_chunk))

    rejoined = "\n\n".join(processed_lines)

    # 2. Split by punctuation + whitespace
    sentences = re.split(r"([.!?]+(?:\s+|\n+))", rejoined)

    # Reassemble sentences with their punctuation
    result = []
    for i in range(0, len(sentences) - 1, 2):
        s = (sentences[i] + sentences[i + 1]).strip()
        if len(s) > 10:
            result.append(s)

    if len(sentences) % 2 == 1:
        s = sentences[-1].strip()
        if len(s) > 10:
            result.append(s)

    return result


def _extract_metadata_from_header(text: str) -> dict:
    """Extract Title, Author, and Language from Gutenberg header (first 100 lines)."""
    lines = text.splitlines()[:100]
    metadata = {"title": None, "author": None, "language": None}

    for line in lines:
        if line.startswith("Title:"):
            metadata["title"] = line.replace("Title:", "").strip()
        elif line.startswith("Author:"):
            metadata["author"] = line.replace("Author:", "").strip()
        elif line.startswith("Language:"):
            metadata["language"] = line.replace("Language:", "").strip()

    return metadata


def align_books(
    gutenberg_files: List[str],
    counterpart_files: List[str] = None,
    ben_yehuda_files: List[str] = None,
    aligned_catalogs: pd.DataFrame = None,
) -> pd.DataFrame:
    """
    Ingest and align books from the Gutenberg download list and Ben Yehuda dump.
    Uses Semantic Title Matching and Catalog-based matches.

    Args:
        gutenberg_files: List of file paths to downloaded books.
        counterpart_files: Optional list of targeted counterpart downloads.
        ben_yehuda_files: Optional list of Ben Yehuda downloads.
        aligned_catalogs: Optional DataFrame of pre-aligned book metadata.

    Returns:
        DataFrame with aligned sentence pairs ['source_es', 'target_he', 'similarity', 'source_book', 'target_book'].
    """
    # Merge file lists
    all_files = gutenberg_files + (counterpart_files or []) + (ben_yehuda_files or [])

    # Organize by language
    es_files = [f for f in all_files if "\\es\\" in f or "/es/" in f or "_es_" in f]
    he_files = [
        f for f in all_files if "\\he\\" in f or "/he/" in f or "_he_" in f or "ben_yehuda" in f
    ]

    logger.info(
        f"Scanning for alignments among {len(es_files)} Spanish and {len(he_files)} Hebrew books."
    )

    # Load Model (LaBSE is standard for bitext mining and cross-lingual similarity)
    model_name = "sentence-transformers/LaBSE"
    logger.info(f"Loading alignment model: {model_name}")
    model = SentenceTransformer(model_name)

    matched_pairs = []

    # --- Step 1: Catalog-based Matching (High Confidence) ---
    if aligned_catalogs is not None and not aligned_catalogs.empty:
        logger.info(f"Processing {len(aligned_catalogs)} catalog-based matches...")

        # Build lookup for files by ID
        # Gutenberg files: {id}_{title}.txt
        gutenberg_lookup = {}
        for f in es_files:
            path = Path(f)
            try:
                bid = path.stem.split("_")[0]
                gutenberg_lookup[int(bid)] = f
            except (ValueError, IndexError):
                continue

        # Ben Yehuda dump path
        ben_yehuda_dump_base = Path("data/01_raw/ben_yehuda_dump/txt_stripped")

        for _, row in aligned_catalogs.iterrows():
            gid = row.get("gutenberg_id")
            byid = row.get("benyehuda_id")

            es_file = gutenberg_lookup.get(gid)

            he_file = None
            if byid:
                # Find matching file in dump
                potential_files = list(ben_yehuda_dump_base.glob(f"**/m{byid}.txt"))
                if potential_files:
                    he_file = str(potential_files[0])

            if es_file and he_file:
                logger.info(f"CATALOG MATCH: {row['match_title']} <-> {row['he_title']}")
                matched_pairs.append((es_file, he_file))

    # --- Step 2: Semantic Title Matching (Fallback/Discovery) ---
    if not matched_pairs:
        logger.info("Performing Semantic Title Matching (Fallback)...")

        def extract_title(filepath):
            path = Path(filepath)
            if path.suffix == ".json":
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    return data.get("title", path.stem)
                except Exception:
                    return path.stem
            name = path.stem
            parts = name.split("_", 1)
            title = parts[1] if len(parts) > 1 else name
            return title.replace("-", " ").replace("_", " ")

        if es_files and he_files:
            es_titles = [extract_title(f) for f in es_files]
            he_titles = [extract_title(f) for f in he_files]

            es_title_embeddings = model.encode(es_titles, convert_to_tensor=True)
            he_title_embeddings = model.encode(he_titles, convert_to_tensor=True)

            cosine_scores = util.cos_sim(es_title_embeddings, he_title_embeddings)
            title_similarity_threshold = 0.70

            for i, es_title in enumerate(es_titles):
                best_score_idx = torch.argmax(cosine_scores[i]).item()
                best_score = cosine_scores[i][best_score_idx].item()

                if best_score > title_similarity_threshold:
                    matched_pairs.append((es_files[i], he_files[best_score_idx]))

    if not matched_pairs:
        logger.warning("No book pairs identified for alignment.")
        return pd.DataFrame(
            columns=["source_es", "target_he", "similarity", "source_book", "target_book"]
        )

    # Dedup pairs
    matched_pairs = list(set(matched_pairs))
    logger.info(f"Finalizing alignment for {len(matched_pairs)} book pairs.")

    # --- Step 3: Validate Matched Pairs ---
    validator = BookPairValidator(model=model)
    validated_pairs = []

    logger.info(f"Validating {len(matched_pairs)} book pairs...")
    for src_file, tgt_file in matched_pairs:
        src_path = Path(src_file)
        tgt_path = Path(tgt_file)

        # Quick pre-validation: read and segment
        try:
            src_text = src_path.read_text(encoding="utf-8", errors="replace")
            tgt_text = tgt_path.read_text(encoding="utf-8", errors="replace")

            src_sents = _segment_sentences_es(src_text)
            tgt_sents = _segment_sentences_he(tgt_text)

            # Extract metadata from headers
            src_meta = _extract_metadata_from_header(src_text)
            tgt_meta = _extract_metadata_from_header(tgt_text)

            # Use header title if available, fallback to filename
            src_title = src_meta["title"] or (
                src_path.stem.split("_", 1)[1] if "_" in src_path.stem else src_path.stem
            )
            tgt_title = tgt_meta["title"] or tgt_path.stem

            # Validate (sample first 200 sentences for speed)
            validation = validator.validate_pair(
                spanish_sentences=src_sents[:200],
                hebrew_sentences=tgt_sents[:200],
                spanish_title=src_title,
                hebrew_title=tgt_title,
                spanish_file=src_path.name,
                hebrew_file=tgt_path.name,
            )

            logger.info(
                f"Validation: {src_path.name} <-> {tgt_path.name} | "
                f"Confidence: {validation['confidence']:.2f} | "
                f"Recommendation: {validation['recommendation']}"
            )

            # Show key signals
            signals = validation["signals"]
            logger.info(
                f"  Signals: Ratio={signals.get('sentence_ratio', 0):.2f}, "
                f"Content={signals.get('content_alignment', 0):.2f}, "
                f"Title={signals.get('title_similarity', 0):.2f}"
            )

            # Show warnings
            for warning in validation["warnings"]:
                logger.warning(f"  {warning}")

            # Only process if valid
            if validation["recommendation"] == "approve":
                validated_pairs.append((src_file, tgt_file, src_sents, tgt_sents))
                logger.info("  ✅ AUTO-APPROVED for alignment")
            elif validation["recommendation"] == "review":
                validated_pairs.append((src_file, tgt_file, src_sents, tgt_sents))
                logger.warning("  ⚠️  FLAGGED for manual review but proceeding")
            else:
                logger.error("  ❌ REJECTED - skipping alignment")

        except Exception as e:
            logger.error(f"Failed to validate {src_path.name} <-> {tgt_path.name}: {e}")
            continue

    logger.info(f"Validation complete: {len(validated_pairs)}/{len(matched_pairs)} pairs approved")

    # --- Step 4: Content Alignment for Validated Pairs ---
    aligned_data = []
    vector_store = VectorStore()

    logger.info(f"Starting content alignment for {len(validated_pairs)} validated pairs...")
    for src_file, tgt_file, src_sents, tgt_sents in tqdm(validated_pairs, desc="Aligning Books"):
        src_path = Path(src_file)
        tgt_path = Path(tgt_file)

        logger.info(f"Aligning content: {src_path.name} <-> {tgt_path.name}")
        logger.info(f"Sentences: {len(src_sents)} (ES) x {len(tgt_sents)} (HE)")

        # Compute or fetch sentence embeddings
        # ES
        src_cached = vector_store.get_cached_embeddings(src_sents, "es", src_path.stem)
        src_missing = [s for s in src_sents if vector_store._get_hash(s) not in src_cached]

        if src_missing:
            logger.info(f"Encoding {len(src_missing)} new Spanish sentences...")
            src_new_emb = model.encode(
                src_missing, batch_size=32, show_progress_bar=True, convert_to_tensor=False
            )
            src_meta = [{"source": src_path.name, "type": "sentence"} for _ in src_missing]
            vector_store.upsert_embeddings(src_missing, src_new_emb, "es", src_path.stem, src_meta)
            for s, emb in zip(src_missing, src_new_emb):
                src_cached[vector_store._get_hash(s)] = emb

        src_emb = torch.tensor(
            np.array([src_cached[vector_store._get_hash(s)] for s in src_sents])
        ).to(model.device)

        # HE
        tgt_cached = vector_store.get_cached_embeddings(tgt_sents, "he", tgt_path.stem)
        tgt_missing = [s for s in tgt_sents if vector_store._get_hash(s) not in tgt_cached]

        if tgt_missing:
            logger.info(f"Encoding {len(tgt_missing)} new Hebrew sentences...")
            tgt_new_emb = model.encode(
                tgt_missing, batch_size=32, show_progress_bar=True, convert_to_tensor=False
            )
            tgt_meta = [{"source": tgt_path.name, "type": "sentence"} for _ in tgt_missing]
            vector_store.upsert_embeddings(tgt_missing, tgt_new_emb, "he", tgt_path.stem, tgt_meta)
            for s, emb in zip(tgt_missing, tgt_new_emb):
                tgt_cached[vector_store._get_hash(s)] = emb

        tgt_emb = torch.tensor(
            np.array([tgt_cached[vector_store._get_hash(s)] for s in tgt_sents])
        ).to(model.device)

        # Mine bitext
        # Use 0.70 as base threshold for classic literature/adaptations
        # Fallback to 0.65 if 0 results
        threshold = 0.70
        hits = util.semantic_search(src_emb, tgt_emb, top_k=1)

        # Check if we have matches at base threshold
        temp_aligned = []
        for i, hit in enumerate(hits):
            if hit and hit[0]["score"] > threshold:
                tgt_idx = hit[0]["corpus_id"]
                temp_aligned.append(
                    {
                        "source_es": src_sents[i],
                        "target_he": tgt_sents[tgt_idx],
                        "similarity": hit[0]["score"],
                        "source_book": src_path.name,
                        "target_book": tgt_path.name,
                    }
                )

        # Fallback if zero matches
        if not temp_aligned:
            logger.info(f"  No matches at {threshold}, trying fallback 0.65...")
            threshold = 0.65
            for i, hit in enumerate(hits):
                if hit and hit[0]["score"] > threshold:
                    tgt_idx = hit[0]["corpus_id"]
                    temp_aligned.append(
                        {
                            "source_es": src_sents[i],
                            "target_he": tgt_sents[tgt_idx],
                            "similarity": hit[0]["score"],
                            "source_book": src_path.name,
                            "target_book": tgt_path.name,
                        }
                    )

        if temp_aligned:
            aligned_data.extend(temp_aligned)
            logger.info(f"  Aligned {len(temp_aligned)} sentences at threshold {threshold}")
        else:
            logger.warning(
                f"  Zero aligned sentences found for {src_path.name} <-> {tgt_path.name}"
            )

    logger.info(f"Total aligned sentences generated: {len(aligned_data)}")
    return pd.DataFrame(aligned_data)
