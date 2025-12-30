import logging

import numpy as np
import pandas as pd
import torch
from fuzzywuzzy import fuzz
from sentence_transformers import SentenceTransformer, util

from .wikidata_utils import fetch_wikidata_labels

logger = logging.getLogger(__name__)


def enrich_benyehuda_with_wikidata(benyehuda_catalog: pd.DataFrame) -> pd.DataFrame:
    """
    Enrich Ben Yehuda catalog with metadata from Wikidata.
    Specifically, fetches English labels for Authors using 'author_uris'.
    """
    if benyehuda_catalog.empty:
        return benyehuda_catalog

    logger.info("Enriching Ben Yehuda catalog with Wikidata...")

    # Extract QIDs from author_uris (e.g., https://wikidata.org/wiki/Q123)
    def extract_qid(uri):
        if pd.isna(uri) or "wikidata.org" not in str(uri):
            return None
        # Handle cases like "https://wikidata.org/wiki/Q123" or just "Q123" or multiple?
        # Assuming single URI for now based on CSV review
        return str(uri).split("/")[-1]

    if "author_uris" in benyehuda_catalog.columns:
        benyehuda_catalog["author_qid"] = benyehuda_catalog["author_uris"].apply(extract_qid)
    else:
        logger.warning("'author_uris' column missing in Ben Yehuda catalog.")
        benyehuda_catalog["author_en"] = ""
        return benyehuda_catalog

    # Get unique QIDs
    unique_qids = benyehuda_catalog["author_qid"].dropna().unique().tolist()

    if not unique_qids:
        logger.warning("No Wikidata QIDs found for Authors.")
        benyehuda_catalog["author_en"] = ""
        return benyehuda_catalog

    # Fetch Labels
    labels_map = fetch_wikidata_labels(unique_qids, languages=["en", "es"])

    # Map back to DataFrame
    def get_label(qid, lang="en"):
        if not qid or qid not in labels_map:
            return None
        return labels_map[qid].get(lang)

    benyehuda_catalog["author_en"] = benyehuda_catalog["author_qid"].apply(
        lambda q: get_label(q, "en")
    )
    benyehuda_catalog["author_es"] = benyehuda_catalog["author_qid"].apply(
        lambda q: get_label(q, "es")
    )

    # Fill NA with empty string for safety
    benyehuda_catalog["author_en"] = benyehuda_catalog["author_en"].fillna("")
    benyehuda_catalog["author_es"] = benyehuda_catalog["author_es"].fillna("")

    # Log success rate
    found = len(benyehuda_catalog[benyehuda_catalog["author_en"] != ""])
    logger.info(f"Enriched {found}/{len(benyehuda_catalog)} records with English Author Names.")
    return benyehuda_catalog


def align_catalogs_bert(
    benyehuda_catalog: pd.DataFrame, gutenberg_catalog: pd.DataFrame, threshold: float = 0.8
) -> pd.DataFrame:
    """
    Align Ben Yehuda catalog (Hebrew) with Gutenberg catalogs (English/Spanish)
    using BERT semantic similarity on Titles, refined by Author matching.
    """
    if SentenceTransformer is None:
        logger.error("sentence-transformers not installed.")
        return pd.DataFrame()

    if benyehuda_catalog.empty or gutenberg_catalog.empty:
        logger.warning("One or both catalogs are empty. Skipping alignment.")
        return pd.DataFrame()

    model_name = "paraphrase-multilingual-MiniLM-L12-v2"
    logger.info(f"Loading BERT model: {model_name}...")
    model = SentenceTransformer(model_name)

    # Normalize Gutenberg authors for search
    gutenberg_catalog["authors_norm"] = gutenberg_catalog["authors"].astype(str).str.lower()

    # Filter targets
    targets = gutenberg_catalog[gutenberg_catalog["language"].isin(["en", "es"])].copy()
    if targets.empty:
        return pd.DataFrame()

    # Prepare embeddings
    he_titles = benyehuda_catalog["title"].fillna("").astype(str).tolist()
    he_ids = benyehuda_catalog["benyehuda_id"].tolist()
    he_authors_en = benyehuda_catalog.get(
        "author_en", pd.Series([""] * len(benyehuda_catalog))
    ).tolist()
    he_langs_origin = benyehuda_catalog.get(
        "language_origin", pd.Series([""] * len(benyehuda_catalog))
    ).tolist()

    logger.info(f"Encoding {len(he_titles)} Ben Yehuda titles...")
    he_embeddings = model.encode(he_titles, convert_to_tensor=True, show_progress_bar=False)

    target_titles = targets["title"].fillna("").astype(str).tolist()
    target_ids = targets["gutenberg_id"].tolist()
    target_langs = targets["language"].tolist()
    target_authors = targets["authors"].astype(str).tolist()
    target_downloads = targets["download_count"].fillna(0).tolist()

    logger.info(f"Encoding {len(target_titles)} Gutenberg titles...")
    target_embeddings = model.encode(target_titles, convert_to_tensor=True, show_progress_bar=True)

    matches = []

    logger.info("Starting Semantic Alignment with Author Refinement...")

    # Convert to standard python list for faster loop than pandas
    # We iterate Ben Yehuda books

    for i in range(len(he_titles)):
        author_en = he_authors_en[i]
        lang_origin = str(he_langs_origin[i]).lower()
        is_translation = lang_origin != "" and lang_origin != "he" and lang_origin != "nan"
        if he_ids[i] == 11229:
            logger.info(
                f"DEBUG: Found 11229. is_translation={is_translation}, origin={lang_origin}, title={he_titles[i]}, author_en={author_en}"
            )
        if is_translation and "quijot" in he_titles[i].lower() or "quishot" in he_titles[i].lower():
            logger.info(
                f"DEBUG: Found translation candidate: {he_titles[i]} (Origin: {lang_origin})"
            )

        # Get Hebrew author name for additional verification
        he_author = str(benyehuda_catalog.iloc[i].get("authors", "")).lower()

        valid_candidates = False
        candidate_indices = []

        # 1. Strategy: Author Filtering
        if author_en and len(author_en) > 2:
            parts = author_en.lower().split()
            surname = parts[-1]

            # Strict Surname Check
            # Prevent "Mani" matching "Maria" or "Human"
            if len(surname) <= 4:
                # Very short surname: Require Exact Match as a standalone word
                candidate_indices = [
                    idx
                    for idx, auth in enumerate(target_authors)
                    if f" {surname} " in f" {auth.lower()} "  # Middle
                    or auth.lower().startswith(f"{surname} ")  # Start
                    or auth.lower().endswith(f" {surname}")  # End
                ]
            else:
                # Normal length: check for inclusion
                candidate_indices = [
                    idx for idx, auth in enumerate(target_authors) if surname in auth.lower()
                ]

            if len(candidate_indices) > 0:
                valid_candidates = True

        # 2. Fallback: If no author match (or no author info), do we do global search?
        # Global search is dangerous (False Positives).
        # But if the threshold is extremely high (0.95), maybe okay?
        # For now, let's allow Global Search BUT maybe with higher threshold?
        # Or just skip? Unsafe.
        # Let's Skip Global Search to avoid "Love" matching "Love".
        # We only match if we have SOME Author signal.
        # Check Ben Yehuda CSV: Do we have authors for everything? Mostly yes.
        # If we fail to fetch Wikidata label, we might have Hebrew Author Name.
        # We could try to embed Hebrew Author and match against English Author?
        # That's advanced.
        # For now, if no candidate indices, we skip (conservative).

        if not valid_candidates:
            if is_translation:
                # If it's a translation, we "give it for granted" that it matches something
                # so we search the entire Gutenberg target set (Global Search)
                # but we use a slightly higher threshold or trust the user's intent.
                candidate_indices = list(range(len(target_titles)))
            else:
                # logger.debug(f"Skipping {he_titles[i]} - No author match found.")
                continue

        # subset embeddings
        cand_tensor = target_embeddings[candidate_indices]
        query_tensor = he_embeddings[i].unsqueeze(0)

        scores = util.cos_sim(query_tensor, cand_tensor)

        # Get top-k results to check for ambiguity
        # If we have an author match or it's a translation, we check more candidates
        top_k_limit = 50 if (valid_candidates or is_translation) else 5
        top_k = min(top_k_limit, scores.shape[1])
        top_vals, top_indices_rel = torch.topk(scores, k=top_k, dim=1)

        best_idx_rel = top_indices_rel[0][0].item()
        best_score = top_vals[0][0].item()

        # Disambiguation Logic: If multiple close title matches, or if we are in global search
        if top_k > 1:
            best_author_score = -1
            best_idx_refined = best_idx_rel

            # If we have author info, use it to pick between top title candidates
            if author_en or (not valid_candidates and is_translation):
                author_to_check = author_en.lower() if author_en else ""

                for k_idx in range(top_k):
                    rel_idx = top_indices_rel[0][k_idx].item()
                    abs_idx = candidate_indices[rel_idx]
                    cand_author = target_authors[abs_idx].lower()
                    cand_title_score = top_vals[0][k_idx].item()

                    # Only consider candidates with title score reasonably close to the best
                    # For translations, we allow a wider gap to let popularity/substring match work
                    score_gap_limit = 0.20 if is_translation else 0.05
                    if cand_title_score < (best_score - score_gap_limit):
                        break

                    # Fuzzy author match score
                    auth_score = (
                        fuzz.token_set_ratio(author_to_check, cand_author) if author_to_check else 0
                    )

                    # Popularity boost (log scale) to favor canonical works in case of title ambiguity
                    # For translations, we are even more aggressive with popularity (canonical works)
                    pop_weight = 0.05 if is_translation else 0.02
                    pop_boost = pop_weight * np.log1p(target_downloads[abs_idx])

                    # Substring match boost for titles (case-insensitive)
                    # Helps with "Don Quijote" vs "Don Quixote"
                    title_match_boost = 0
                    cand_title_lower = target_titles[abs_idx].lower()
                    he_title_lower = he_titles[i].lower()

                    if "don " in he_title_lower and "don " in cand_title_lower:
                        title_match_boost += 0.05
                    if "quijot" in cand_title_lower and (
                        "quixot" in he_title_lower or "קישוט" in he_titles[i]
                    ):
                        title_match_boost += 0.10

                    # Short title penalty: help avoid false positives for short words like "Ayala"
                    # Phonetic similarity between short names often leads to high semantic scores
                    # Apply stronger penalty for very short titles in global search
                    short_title_penalty = 0
                    if not valid_candidates:  # Global search mode
                        if len(he_title_lower) <= 5:
                            short_title_penalty = -0.30  # Very strong penalty for very short titles
                        elif len(he_title_lower) <= 8:
                            short_title_penalty = -0.20  # Strong penalty for short titles

                    # Cross-lingual Author Verification (Heuristic)
                    # If we have a Hebrew author name, and we are in global search (no Wikidata match),
                    # we check if the surname appears in any form.
                    author_conflict_penalty = 0
                    if not valid_candidates and he_author:
                        # This is conservative: only penalize if we're sure they are DIFFERENT.
                        # For example, if He-Author is clearly not Homer but we match Iliada.
                        author_conflicts = [
                            ("הומרוס", "homer"),
                            ("סרוונטס", "cervantes"),
                            ("שייקספיר", "shakespeare"),
                            ("טולסטוי", "tolstoy"),
                            ("דוסטויבסקי", "dostoevsky"),
                            ("דיקנס", "dickens"),
                            ("ברונטה", "bronte"),
                            ("אוסטן", "austen"),
                        ]
                        for he_name, en_name in author_conflicts:
                            if he_name in he_author and en_name not in cand_author:
                                author_conflict_penalty = -0.40  # Strong penalty for known mismatch
                                break

                    # Calculate total adjustments
                    total_boost = (auth_score / 100.0 * 0.2) + pop_boost + title_match_boost
                    total_penalty = short_title_penalty + author_conflict_penalty

                    # In global search mode (no author filtering), cap total positive boost
                    # to prevent inflating low-quality matches above threshold
                    if not valid_candidates:
                        total_boost = min(total_boost, 0.10)  # Cap boost at 0.10 for global search

                    adjusted_score = cand_title_score + total_boost + total_penalty

                    if adjusted_score > best_author_score:
                        best_author_score = adjusted_score
                        best_idx_refined = rel_idx

                best_idx_rel = best_idx_refined
                best_score = scores[0][best_idx_rel].item()

        # Determine threshold
        # If we have a validated author match, we can be much more lenient with the title
        # especially for cross-language transliterations (e.g. Quijote vs Quishot)
        if valid_candidates:
            current_threshold = max(0.40, threshold - 0.35)
        elif is_translation:
            # Global search for identified translation (no author match) requires extremely high confidence
            # to avoid phonetic/semantic traps for common short words like "Ayala" vs "Iliada".
            current_threshold = max(0.95, threshold)
        else:
            current_threshold = threshold

        if best_score >= current_threshold:
            best_idx_abs = candidate_indices[best_idx_rel]

            matches.append(
                {
                    "benyehuda_id": he_ids[i],
                    "he_title": he_titles[i],
                    "gutenberg_id": target_ids[best_idx_abs],
                    "match_title": target_titles[best_idx_abs],
                    "match_language": target_langs[best_idx_abs],
                    "score": best_score,
                    "author_filtered": valid_candidates,
                    "is_translation": is_translation,
                }
            )

    df_matches = pd.DataFrame(matches)
    # The 'id' column is handled by Kedro's index: true, index_label: id configuration in catalog.yml
    # Adding it here manually causes a conflict during SQL save.
    logger.info(f"Found {len(df_matches)} validated alignments.")
    return df_matches
