"""Nodes for formatting final dictionary output.

This module creates the final JSON output with metadata and proper structure.
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


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

    return json.dumps(dictionary, ensure_ascii=False, indent=2)
