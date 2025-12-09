"""Metrics pipeline for alignment statistics and visualizations."""

from kedro.pipeline import Pipeline, node

from .nodes import compute_alignment_stats, create_alignment_visualizations, create_progress_summary


def create_pipeline(**kwargs) -> Pipeline:
    """Create the alignment metrics pipeline.

    This pipeline computes statistics and creates visualizations for the
    language alignment phase, and creates an overall progress summary.

    Returns:
        Pipeline with alignment statistics and visualization nodes.
    """
    return Pipeline(
        [
            node(
                func=compute_alignment_stats,
                inputs=["aligned_matches", "enriched_entries"],
                outputs="alignment_stats",
                name="compute_alignment_stats_node",
                tags=["metrics", "statistics", "alignment"],
            ),
            node(
                func=create_alignment_visualizations,
                inputs="alignment_stats",
                outputs="alignment_visualizations",
                name="create_alignment_viz_node",
                tags=["metrics", "visualization", "alignment"],
            ),
            node(
                func=create_progress_summary,
                inputs=["parsing_stats", "alignment_stats"],
                outputs="progress_summary",
                name="create_progress_summary_node",
                tags=["metrics", "summary", "reporting"],
            ),
        ]
    )
