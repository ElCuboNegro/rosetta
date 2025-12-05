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
    hebrew_df: pd.DataFrame
) -> pd.DataFrame:
    """Align Spanish words with Hebrew translations.
    
    Uses both explicit translation links from Wiktionary and fuzzy matching
    to create strong alignments between Spanish and Hebrew entries.
    
    Args:
        spanish_df: Spanish entries with translations_he field.
        hebrew_df: Hebrew entries with translations_es field.
        
    Returns:
        DataFrame with aligned word pairs containing all relevant fields.
    """
    logger.info("Aligning Spanish and Hebrew entries...")
    
    alignments = []
    
    for _, es_row in spanish_df.iterrows():
        # Get explicit translations from Wiktionary
        he_translations = es_row.get("translations_he", [])
        
        for i, he_word in enumerate(he_translations):
            # Find matching Hebrew entry
            he_match = hebrew_df[hebrew_df["word"] == he_word]
            
            if not he_match.empty:
                he_entry = he_match.iloc[0]
                # Determine sense_id based on which definition this is
                sense_id = i + 1
                
                alignments.append({
                    "es_word": es_row["word"],
                    "es_ipa": es_row["ipa"],
                    "es_pos": es_row["pos"],
                    "es_definition": es_row["definitions"][i] if i < len(es_row["definitions"]) else es_row["definitions"][0],
                    "he_word": he_word,
                    "he_ipa": he_entry["ipa"],
                    "he_definition": he_entry["definitions"][0] if he_entry["definitions"] else "",
                    "sense_id": sense_id
                })
            else:
                # Fuzzy match if no exact match found
                logger.warning(f"No exact match for '{he_word}', considering fuzzy matching")
    
    df = pd.DataFrame(alignments)
    logger.info(f"Created {len(df)} aligned word pairs")
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
