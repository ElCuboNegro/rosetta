"""Architect pipeline nodes for final dictionary formatting.

This module creates the final JSON output with metadata and proper structure.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def generate_hebrew_ipa(aligned_data: List[Dict[str, Any]],
                        params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate Hebrew IPA pronunciations for dictionary entries.
    
    Uses the phonikud library for Modern Israeli Hebrew pronunciation,
    with rule-based fallback for cases where phonikud is unavailable.
    
    Args:
        aligned_data: List of structured dictionary entries from aligner.
        params: Parameters from conf/base/parameters_reporting.yml
        
    Returns:
        Dictionary entries with generated Hebrew IPA pronunciations.
    """
    from .hebrew_ipa_generator import generate_hebrew_ipa_for_entries

    logger.info("Generating Hebrew IPA pronunciations...")

    # Extract parameters
    hebrew_ipa_params = params.get("hebrew_ipa", {})
    variant = hebrew_ipa_params.get("default_variant", "modern")
    skip_existing = hebrew_ipa_params.get("skip_existing", True)

    # Generate IPA
    updated_data = generate_hebrew_ipa_for_entries(
        aligned_data,
        variant=variant,
        skip_existing=skip_existing
    )

    logger.info("Hebrew IPA generation complete")

    return updated_data


def format_final_json(aligned_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Construct the final dictionary JSON with metadata.
    
    Takes the structured list of dictionary entries and wraps them in
    the final JSON format with metadata including version, source, and date.
    
    Args:
        aligned_data: List of structured dictionary entries from aligner.
        
    Returns:
        Complete dictionary JSON matching the user's exact specification.
    """
    logger.info("Formatting final dictionary JSON...")

    dictionary = {
        "metadata": {
            "language_direction": "es-he | he-es",
            "version": "1.0",
            "source": "custom (Wiktionary + Tatoeba)",
            "generated_at": datetime.now().strftime("%Y-%m-%d")
        },
        "entries": aligned_data
    }

    total_entries = len(aligned_data)
    total_senses = sum(len(entry["entry"]["senses"]) for entry in aligned_data)

    logger.info(
        f"Final dictionary contains {total_entries} unique words "
        f"with {total_senses} total senses"
    )

    return dictionary
