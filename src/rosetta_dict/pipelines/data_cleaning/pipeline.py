"""Data cleaning pipeline for filtering unwanted entries."""

from kedro.pipeline import Pipeline, node

from .nodes import filter_proper_nouns


def create_pipeline(**kwargs) -> Pipeline:
    """Create the data cleaning pipeline.

    This pipeline filters out proper nouns (names, places) from parsed
    Wiktionary entries using POS tags and capitalization heuristics.

    Returns:
        Pipeline with filtering nodes for each language.
    """
    return Pipeline(
        [
            node(
                func=filter_proper_nouns,
                inputs="raw_spanish_entries_unfiltered",
                outputs="raw_spanish_entries_filtered",
                name="filter_spanish_proper_nouns_node",
                tags=["cleaning", "filtering", "spanish"],
            ),
            node(
                func=filter_proper_nouns,
                inputs="raw_hebrew_entries_unfiltered",
                outputs="raw_hebrew_entries_filtered",
                name="filter_hebrew_proper_nouns_node",
                tags=["cleaning", "filtering", "hebrew"],
            ),
        ]
    )
