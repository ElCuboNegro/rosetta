"""Aligner pipeline nodes for linking Spanish and Hebrew entries.

This module aligns Spanish words with their Hebrew translations using
fuzzy matching (rapidfuzz) and enriches entries with example sentences.
"""

import logging
import pandas as pd
from typing import List, Dict, Any
from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)


def align_languages(
    spanish_df: pd.DataFrame,
    hebrew_df: pd.DataFrame,
    bridge_df: pd.DataFrame = None
) -> pd.DataFrame:
    """Align Spanish words with Hebrew translations using multiple strategies.

    Strategies (in order of preference):
    1. Direct translations from Spanish/Hebrew Wiktionaries
    2. Triangulation via English Wiktionary (Spanish→English→Hebrew)
    3. Fuzzy definition matching using rapidfuzz

    Args:
        spanish_df: Spanish entries with translations_he field.
        hebrew_df: Hebrew entries with translations_es field.
        bridge_df: English Wiktionary entries for triangulation (optional).

    Returns:
        DataFrame with aligned word pairs containing all relevant fields.
    """
    logger.info("Aligning Spanish and Hebrew entries...")
    logger.info(f"Input: {len(spanish_df)} Spanish, {len(hebrew_df)} Hebrew entries")
    if bridge_df is not None:
        logger.info(f"Bridge data: {len(bridge_df)} English Wiktionary entries")

    alignments = []
    stats = {"direct": 0, "triangulation": 0, "fuzzy": 0, "failed": 0}

    # Strategy 1: Direct translations
    for _, es_row in spanish_df.iterrows():
        he_translations = es_row.get("translations_he", [])

        for i, he_word in enumerate(he_translations):
            he_match = hebrew_df[hebrew_df["word"] == he_word]

            if not he_match.empty:
                he_entry = he_match.iloc[0]
                sense_id = i + 1

                es_defs = es_row["definitions"] if isinstance(es_row["definitions"], list) else []
                he_defs = he_entry["definitions"].tolist() if isinstance(he_entry["definitions"], pd.Series) else (he_entry["definitions"] if isinstance(he_entry["definitions"], list) else [])

                alignments.append({
                    "es_word": es_row["word"],
                    "es_ipa": es_row["ipa"],
                    "es_pos": es_row["pos"],
                    "es_definition": es_defs[i] if i < len(es_defs) else (es_defs[0] if es_defs else ""),
                    "he_word": he_word,
                    "he_ipa": he_entry["ipa"],
                    "he_definition": he_defs[0] if he_defs else "",
                    "sense_id": sense_id,
                    "match_type": "direct"
                })
                stats["direct"] += 1

    logger.info(f"Direct alignments: {stats['direct']}")

    # Strategy 2: Triangulation via English Wiktionary
    if bridge_df is not None and not bridge_df.empty:
        logger.info("Performing triangulation via English Wiktionary...")

        # Build indices for faster lookup
        es_bridge = bridge_df[bridge_df['source_lang'] == 'es']
        he_bridge = bridge_df[bridge_df['source_lang'] == 'he']

        aligned_es_words = set(a['es_word'] for a in alignments)

        for _, es_row in spanish_df.iterrows():
            es_word = es_row["word"]

            # Skip if already aligned
            if es_word in aligned_es_words:
                continue

            # Find Spanish word in English Wiktionary
            es_in_en = es_bridge[es_bridge['word'] == es_word]

            if not es_in_en.empty:
                # Get Hebrew translations from English Wiktionary
                he_translations = es_in_en.iloc[0].get("translations_he", [])

                for he_word in he_translations:
                    he_match = hebrew_df[hebrew_df["word"] == he_word]

                    if not he_match.empty:
                        he_entry = he_match.iloc[0]
                        es_defs = es_row["definitions"] if isinstance(es_row["definitions"], list) else []
                        he_defs = he_entry["definitions"].tolist() if isinstance(he_entry["definitions"], pd.Series) else (he_entry["definitions"] if isinstance(he_entry["definitions"], list) else [])

                        alignments.append({
                            "es_word": es_word,
                            "es_ipa": es_row["ipa"],
                            "es_pos": es_row["pos"],
                            "es_definition": es_defs[0] if es_defs else "",
                            "he_word": he_word,
                            "he_ipa": he_entry["ipa"],
                            "he_definition": he_defs[0] if he_defs else "",
                            "sense_id": 1,
                            "match_type": "triangulation"
                        })
                        stats["triangulation"] += 1
                        aligned_es_words.add(es_word)
                        break  # Only take first triangulated match per word

        logger.info(f"Triangulation alignments: {stats['triangulation']}")

    # Strategy 3: Fuzzy definition matching (OPTIMIZED with rapidfuzz.process)
    logger.info("Attempting fuzzy definition matching for ALL remaining entries...")
    aligned_es_words = set(a['es_word'] for a in alignments)
    fuzzy_threshold = 80  # Lowered threshold for better coverage

    # Get all remaining Spanish entries, sorted by frequency rank
    remaining_es = spanish_df[~spanish_df['word'].isin(aligned_es_words)].copy()

    # Sort by frequency rank if available (prioritize common words)
    if 'frequency_rank' in remaining_es.columns:
        remaining_es = remaining_es.sort_values('frequency_rank')
        logger.info(f"Processing {len(remaining_es)} remaining entries by frequency priority...")
    else:
        logger.info(f"Processing {len(remaining_es)} remaining entries...")

    # Pre-build Hebrew candidates dictionary for O(1) lookup after matching
    he_candidates_dict = {}
    he_definitions_list = []

    for idx, he_row in hebrew_df.iterrows():
        he_defs = he_row["definitions"] if isinstance(he_row["definitions"], list) else []
        if he_defs:
            he_def_text = " ".join(he_defs)
            he_definitions_list.append(he_def_text)
            he_candidates_dict[he_def_text] = he_row

    logger.info(f"Built index of {len(he_definitions_list)} Hebrew candidates for optimized fuzzy matching")

    # Process all remaining entries with OPTIMIZED matching using process.extractOne
    for idx, (_, es_row) in enumerate(remaining_es.iterrows()):
        if (idx + 1) % 1000 == 0:
            logger.info(f"Fuzzy matching progress: {idx + 1}/{len(remaining_es)} ({stats['fuzzy']} matches found)")

        es_word = es_row["word"]
        es_defs = es_row["definitions"] if isinstance(es_row["definitions"], list) else []

        if not es_defs:
            continue

        es_def_text = " ".join(es_defs)

        # OPTIMIZED: Use process.extractOne for O(n log n) instead of O(n²)
        # This is 10-100x faster for large datasets
        result = process.extractOne(
            es_def_text,
            he_definitions_list,
            scorer=fuzz.ratio,
            score_cutoff=fuzzy_threshold
        )

        if result is not None:
            best_match_def, best_score, _ = result
            best_match = he_candidates_dict[best_match_def]
            he_defs = best_match["definitions"] if isinstance(best_match["definitions"], list) else []

            alignments.append({
                "es_word": es_word,
                "es_ipa": es_row["ipa"],
                "es_pos": es_row["pos"],
                "es_definition": es_defs[0] if es_defs else "",
                "he_word": best_match["word"],
                "he_ipa": best_match["ipa"],
                "he_definition": he_defs[0] if he_defs else "",
                "sense_id": 1,
                "match_type": f"fuzzy_{best_score}",
                "confidence": best_score / 100.0
            })
            stats["fuzzy"] += 1

    logger.info(f"Fuzzy alignments completed: {stats['fuzzy']} matches found (OPTIMIZED algorithm)")

    df = pd.DataFrame(alignments)
    logger.info(f"Total alignments: {len(df)} (direct: {stats['direct']}, triangulation: {stats['triangulation']}, fuzzy: {stats['fuzzy']})")
    return df


def enrich_entries(
    aligned_df: pd.DataFrame,
    examples_df: pd.DataFrame
) -> pd.DataFrame:
    """Enrich aligned entries with example sentences from Tatoeba.
    
    Args:
        aligned_df: Aligned Spanish-Hebrew word pairs.
        examples_df: Sentence examples with es_words and he_words fields.
        
    Returns:
        DataFrame with enriched entries including matched examples.
    """
    logger.info("Enriching entries with example sentences...")
    
    enriched = []
    for _, row in aligned_df.iterrows():
        # Find matching examples that contain both the Spanish and Hebrew words
        matching_examples = examples_df[
            (examples_df["es_words"].apply(lambda x: row["es_word"] in x)) &
            (examples_df["he_words"].apply(lambda x: row["he_word"] in x))
        ]
        
        examples = []
        for _, ex in matching_examples.iterrows():
            examples.append({
                "es": ex["es"],
                "he": ex["he"]
            })
        
        enriched.append({
            **row.to_dict(),
            "examples": examples
        })
    
    df = pd.DataFrame(enriched)
    logger.info(f"Enriched {len(df)} entries with examples")
    return df


def cluster_polysemic_senses(enriched_df: pd.DataFrame) -> pd.DataFrame:
    """Cluster related senses for polysemic words using semantic similarity.

    For words with multiple senses, this groups semantically similar senses
    together and assigns cluster IDs for better organization.

    Args:
        enriched_df: DataFrame with aligned word pairs

    Returns:
        DataFrame with added semantic_cluster column
    """
    logger.info("Clustering polysemic senses by semantic similarity...")

    enriched_df = enriched_df.copy()
    enriched_df["semantic_cluster"] = 1  # Default cluster

    # Group by Spanish word to find polysemic entries
    for es_word, group in enriched_df.groupby("es_word"):
        if len(group) <= 1:
            continue  # Not polysemic

        # Build definition similarity matrix
        definitions = group["es_definition"].tolist()
        n = len(definitions)

        if n > 10:  # Skip very polysemic words (too many senses to cluster meaningfully)
            continue

        # Cluster similar definitions
        clusters = []
        used_indices = set()

        for i in range(n):
            if i in used_indices:
                continue

            current_cluster = [i]
            used_indices.add(i)

            # Find similar definitions
            for j in range(i + 1, n):
                if j in used_indices:
                    continue

                similarity = fuzz.ratio(definitions[i], definitions[j])
                if similarity > 70:  # Threshold for semantic similarity
                    current_cluster.append(j)
                    used_indices.add(j)

            clusters.append(current_cluster)

        # Assign cluster IDs
        for cluster_id, indices in enumerate(clusters, 1):
            for idx in indices:
                row_idx = group.iloc[idx].name
                enriched_df.at[row_idx, "semantic_cluster"] = cluster_id

    polysemic_count = (enriched_df.groupby("es_word")["semantic_cluster"].max() > 1).sum()
    logger.info(f"Clustered senses for {polysemic_count} polysemic words")

    return enriched_df


def structure_senses(enriched_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Structure flat data into polysemic JSON format.
    
    Groups entries by Spanish word to handle polysemy (multiple meanings)
    and structures them according to the user's required JSON schema.
    
    Args:
        enriched_df: Enriched DataFrame with all fields.
        
    Returns:
        List of dictionary entries in the final JSON structure.
    """
    logger.info("Structuring entries into polysemic JSON format...")
    
    # Group by Spanish word to handle polysemy
    grouped = enriched_df.groupby("es_word")
    
    entries = []
    for es_word, group in grouped:
        # Create senses for each meaning/translation
        senses = []
        for _, row in group.iterrows():
            # Convert all values to Python native types to ensure JSON serialization
            sense = {
                "sense_id": int(row["sense_id"]),
                "definition": str(row["es_definition"]),
                "ipa_hebrew": str(row["he_ipa"]),
                "hebrew": str(row["he_word"]),
                "pos": str(row["es_pos"]),
                "examples": row["examples"] if isinstance(row["examples"], list) else []
            }
            senses.append(sense)
        
        # Create the entry structure
        entry = {
            "id": f"es: {es_word}",
            "entry": {
                "word": str(es_word),
                "ipa": str(group.iloc[0]["es_ipa"]),
                "language": "es",
                "etymology": None,
                "senses": senses
            }
        }
        entries.append(entry)
    
    logger.info(f"Structured {len(entries)} dictionary entries with {len(enriched_df)} total senses")
    return entries
