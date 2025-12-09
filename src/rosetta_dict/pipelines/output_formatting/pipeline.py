"""Output formatting pipeline for final dictionary JSON."""

from kedro.pipeline import Pipeline, node

from .nodes import format_final_json


def create_pipeline(**kwargs) -> Pipeline:
    """Create the output formatting pipeline.

    This pipeline formats the final dictionary JSON with metadata including
    version, source, and generation date.

    Returns:
        Pipeline with JSON formatting node.
    """
    return Pipeline(
        [
            node(
                func=format_final_json,
                inputs="aligned_dictionary_with_ipa",
                outputs="final_dictionary_json",
                name="format_final_json_node",
                tags=["formatting", "output", "json"],
            ),
        ]
    )
