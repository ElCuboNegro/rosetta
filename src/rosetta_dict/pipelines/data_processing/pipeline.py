"""Harvester pipeline for extracting and parsing linguistic data."""

from kedro.pipeline import Node, Pipeline, pipeline

from .nodes import (
    download_wiktionary_dump,
    parse_spanish_wiktionary,
    parse_hebrew_wiktionary,
    process_tatoeba
)
from .stats_nodes import (
    compute_parsing_stats,
    create_parsing_visualizations
)


def create_pipeline(**kwargs) -> Pipeline:
    """Create the harvester pipeline.

    This pipeline:
    1. Downloads Wiktionary dumps (if not already present)
    2. Extracts raw data from dumps and Tatoeba sentences
    3. Parses them into structured DataFrames
    4. Computes statistics and creates visualizations

    Wiktionary configuration is in conf/base/parameters.yml

    Returns:
        Pipeline with download, extraction, and statistics nodes.
    """
    # Core data processing pipeline
    data_pipeline = pipeline(
        [
            # Download dumps if they don't exist
            Node(
                func=download_wiktionary_dump,
                inputs=["params:wiktionary.es_dump_url", "params:wiktionary.es_dump_path"],
                outputs="es_dump_filepath",
                name="download_spanish_dump",
                tags=["download", "data_acquisition"],
            ),
            Node(
                func=download_wiktionary_dump,
                inputs=["params:wiktionary.he_dump_url", "params:wiktionary.he_dump_path"],
                outputs="he_dump_filepath",
                name="download_hebrew_dump",
                tags=["download", "data_acquisition"],
            ),
            # Parse the dumps
            Node(
                func=parse_spanish_wiktionary,
                inputs="es_dump_filepath",
                outputs="raw_spanish_entries",
                name="parse_spanish_wiktionary_node",
                tags=["parsing", "spanish"],
            ),
            Node(
                func=parse_hebrew_wiktionary,
                inputs="he_dump_filepath",
                outputs="raw_hebrew_entries",
                name="parse_hebrew_wiktionary_node",
                tags=["parsing", "hebrew"],
            ),
            Node(
                func=process_tatoeba,
                inputs="tatoeba_sentences",
                outputs="clean_examples",
                name="process_tatoeba_node",
                tags=["parsing", "examples"],
            ),
        ]
    )

    # Statistics and visualization pipeline
    stats_pipeline = pipeline(
        [
            Node(
                func=compute_parsing_stats,
                inputs=["raw_spanish_entries", "raw_hebrew_entries", "clean_examples"],
                outputs="parsing_stats",
                name="compute_parsing_stats_node",
                tags=["statistics", "metrics"],
            ),
            Node(
                func=create_parsing_visualizations,
                inputs="parsing_stats",
                outputs="parsing_visualizations",
                name="create_parsing_viz_node",
                tags=["visualization", "metrics"],
            ),
        ]
    )

    return data_pipeline + stats_pipeline
