"""Bridge data combination pipeline for merging multi-language sources."""

from kedro.pipeline import Pipeline, node

from .nodes import combine_bridge_data


def create_pipeline(**kwargs) -> Pipeline:
    """Create the bridge data combination pipeline.

    This pipeline combines English, French, and German Wiktionary data
    into a single bridge dataset for robust multi-point triangulation.

    Returns:
        Pipeline with bridge data combination node.
    """
    return Pipeline(
        [
            node(
                func=combine_bridge_data,
                inputs=["raw_english_entries", "raw_french_entries", "raw_german_entries"],
                outputs="bridge_entries",
                name="combine_bridge_data_node",
                tags=["bridge", "triangulation", "combination"],
            ),
        ]
    )
