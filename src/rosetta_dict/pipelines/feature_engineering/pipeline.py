"""Feature engineering pipeline for adding computed features."""

from kedro.pipeline import Pipeline, node

from .nodes import add_frequency_ranks


def create_pipeline(**kwargs) -> Pipeline:
    """Create the feature engineering pipeline.

    This pipeline adds frequency ranks to word entries based on multiple signals
    like number of translations, definitions, and word length.

    Returns:
        Pipeline with feature engineering nodes.
    """
    return Pipeline(
        [
            node(
                func=add_frequency_ranks,
                inputs=["raw_spanish_entries_filtered", "raw_hebrew_entries_filtered"],
                outputs=["raw_spanish_entries", "raw_hebrew_entries"],
                name="add_frequency_ranks_node",
                tags=["features", "ranking", "frequency"],
            ),
        ]
    )
