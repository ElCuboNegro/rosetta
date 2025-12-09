"""Wiktionary parsing pipeline for extracting structured data from JSONL files."""

from kedro.pipeline import Pipeline, node

from .nodes import (
    parse_english_wiktionary,
    parse_french_wiktionary,
    parse_german_wiktionary,
    parse_hebrew_wiktionary,
    parse_spanish_wiktionary,
)


def create_pipeline(**kwargs) -> Pipeline:
    """Create the Wiktionary parsing pipeline.

    This pipeline parses pre-extracted kaikki.org JSONL files into structured
    DataFrames with words, IPA, definitions, and translations for all 5 languages
    to enable robust multi-point triangulation.

    Returns:
        Pipeline with parsing nodes for each language.
    """
    return Pipeline(
        [
            node(
                func=parse_spanish_wiktionary,
                inputs="es_dump_filepath",
                outputs="raw_spanish_entries_unfiltered",
                name="parse_spanish_wiktionary_node",
                tags=["parsing", "extraction", "spanish"],
            ),
            node(
                func=parse_hebrew_wiktionary,
                inputs="he_dump_filepath",
                outputs="raw_hebrew_entries_unfiltered",
                name="parse_hebrew_wiktionary_node",
                tags=["parsing", "extraction", "hebrew"],
            ),
            node(
                func=parse_english_wiktionary,
                inputs="en_dump_filepath",
                outputs="raw_english_entries",
                name="parse_english_wiktionary_node",
                tags=["parsing", "extraction", "english", "bridge"],
            ),
            node(
                func=parse_french_wiktionary,
                inputs="fr_dump_filepath",
                outputs="raw_french_entries",
                name="parse_french_wiktionary_node",
                tags=["parsing", "extraction", "french", "bridge"],
            ),
            node(
                func=parse_german_wiktionary,
                inputs="de_dump_filepath",
                outputs="raw_german_entries",
                name="parse_german_wiktionary_node",
                tags=["parsing", "extraction", "german", "bridge"],
            ),
        ]
    )
