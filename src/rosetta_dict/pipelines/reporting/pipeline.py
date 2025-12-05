"""Architect pipeline for final dictionary formatting."""

from kedro.pipeline import Node, Pipeline

from .nodes import format_final_json


def create_pipeline(**kwargs) -> Pipeline:
    """Create the architect pipeline.
    
    This pipeline takes the structured dictionary data and formats it
    into the final JSON output with metadata.
    
    Returns:
        Pipeline with one formatting node.
    """
    return Pipeline(
        [
            Node(
                func=format_final_json,
                inputs="aligned_dictionary",
                outputs="final_dictionary_json",
                name="format_final_json_node",
            ),
        ]
    )
