"""Example processing pipeline for Tatoeba sentences."""

from kedro.pipeline import Pipeline, node

from .nodes import process_tatoeba


def create_pipeline(**kwargs) -> Pipeline:
    """Create the example processing pipeline.

    This pipeline processes Tatoeba sentence pairs for Spanish-Hebrew examples.

    Returns:
        Pipeline with Tatoeba processing node.
    """
    return Pipeline(
        [
            node(
                func=process_tatoeba,
                inputs="tatoeba_sentences",
                outputs="clean_examples",
                name="process_tatoeba_node",
                tags=["examples", "tatoeba", "sentences"],
            ),
        ]
    )
