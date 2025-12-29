import requests
import logging
from typing import List, Dict
import time

logger = logging.getLogger(__name__)


def fetch_wikidata_labels(
    wikidata_ids: List[str], languages: List[str] = ["en", "es"]
) -> Dict[str, Dict[str, str]]:
    """
    Fetch labels (e.g. names) for Wikidata items in specified languages.

    Args:
        wikidata_ids: List of Q IDs (e.g. ['Q42', 'Q123'])
        languages: List of language codes to fetch

    Returns:
        Dict mapping QID -> {lang: label}
        Example: {'Q42': {'en': 'Douglas Adams', 'es': 'Douglas Adams'}}
    """
    # Deduplicate and filter valid IDs
    valid_ids = [qid for qid in set(wikidata_ids) if qid and qid.startswith("Q")]
    if not valid_ids:
        return {}

    base_url = "https://www.wikidata.org/w/api.php"
    results = {}

    # Process in batches of 50 (API limit)
    batch_size = 50
    total_batches = (len(valid_ids) // batch_size) + 1

    logger.info(
        f"Fetching Wikidata labels for {len(valid_ids)} items in {total_batches} batches..."
    )

    for i in range(0, len(valid_ids), batch_size):
        batch = valid_ids[i : i + batch_size]
        ids_str = "|".join(batch)
        langs_str = "|".join(languages)

        params = {
            "action": "wbgetentities",
            "ids": ids_str,
            "props": "labels",
            "languages": langs_str,
            "format": "json",
        }

        headers = {"User-Agent": "RosettaDict/1.0 (Contact: jalbacar@gmail.com)"}

        try:
            resp = requests.get(base_url, params=params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                entities = data.get("entities", {})

                for qid, entity in entities.items():
                    labels = entity.get("labels", {})
                    results[qid] = {}
                    for lang in languages:
                        if lang in labels:
                            results[qid][lang] = labels[lang]["value"]
            else:
                logger.error(f"Wikidata API Error: {resp.status_code}")

            time.sleep(0.5)  # Polite rate limit

        except Exception as e:
            logger.error(f"Error fetching Wikidata batch {i}: {e}")

    return results
