"""Metrics pipeline for parsing statistics and visualizations."""

from kedro.pipeline import Pipeline, node

from .nodes import compute_parsing_stats, create_parsing_visualizations


def create_pipeline(**kwargs) -> Pipeline:
    """Create the parsing metrics pipeline.

    This pipeline computes statistics and creates visualizations for the
    data parsing phase (Wiktionary and Tatoeba processing).

    Returns:
        Pipeline with parsing statistics and visualization nodes.
    """
    return Pipeline(
        [
            node(
                func=compute_parsing_stats,
                inputs=["raw_spanish_entries", "raw_hebrew_entries", "clean_examples"],
                outputs="parsing_stats",
                name="compute_parsing_stats_node",
                tags=["metrics", "statistics", "parsing"],
            ),
            node(
                func=create_parsing_visualizations,
                inputs="parsing_stats",
                outputs="parsing_visualizations",
                name="create_parsing_viz_node",
                tags=["metrics", "visualization", "parsing"],
            ),
        ]
    )
