"""Aligner pipeline for linking and enriching dictionary entries."""

from kedro.pipeline import Node, Pipeline, pipeline

from .nodes import align_languages, enrich_entries, structure_senses
from ..data_processing.stats_nodes import (
    compute_alignment_stats,
    create_alignment_visualizations,
    create_progress_summary
)


def create_pipeline(**kwargs) -> Pipeline:
    """Create the aligner pipeline.

    This pipeline aligns Spanish and Hebrew word entries, enriches them
    with example sentences, structures them into polysemic senses, and
    computes comprehensive statistics.

    Returns:
        Pipeline with alignment, structuring, and statistics nodes.
    """
    # Core alignment pipeline
    alignment_pipeline = pipeline(
        [
            Node(
                func=align_languages,
                inputs=["raw_spanish_entries", "raw_hebrew_entries"],
                outputs="aligned_matches",
                name="align_languages_node",
                tags=["alignment", "matching"],
            ),
            Node(
                func=enrich_entries,
                inputs=["aligned_matches", "clean_examples"],
                outputs="enriched_entries",
                name="enrich_entries_node",
                tags=["enrichment", "examples"],
            ),
            Node(
                func=structure_senses,
                inputs="enriched_entries",
                outputs="aligned_dictionary",
                name="structure_senses_node",
                tags=["structuring", "output"],
            ),
        ]
    )

    # Statistics and visualization pipeline
    stats_pipeline = pipeline(
        [
            Node(
                func=compute_alignment_stats,
                inputs=["aligned_matches", "enriched_entries"],
                outputs="alignment_stats",
                name="compute_alignment_stats_node",
                tags=["statistics", "metrics"],
            ),
            Node(
                func=create_alignment_visualizations,
                inputs="alignment_stats",
                outputs="alignment_visualizations",
                name="create_alignment_viz_node",
                tags=["visualization", "metrics"],
            ),
            Node(
                func=create_progress_summary,
                inputs=["parsing_stats", "alignment_stats"],
                outputs="progress_summary",
                name="create_progress_summary_node",
                tags=["statistics", "summary"],
            ),
        ]
    )

    return alignment_pipeline + stats_pipeline
