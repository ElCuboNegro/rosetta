"""Phonemization pipeline for generating IPA pronunciations."""

from kedro.pipeline import Pipeline, node

from .nodes import generate_hebrew_ipa


def create_pipeline(**kwargs) -> Pipeline:
    """Create the phonemization pipeline.

    This pipeline generates Hebrew IPA pronunciations for entries that are
    missing them using the phonikud library.

    Returns:
        Pipeline with Hebrew IPA generation node.
    """
    return Pipeline(
        [
            node(
                func=generate_hebrew_ipa,
                inputs=["aligned_dictionary", "params:hebrew_ipa"],
                outputs="aligned_dictionary_with_ipa",
                name="generate_hebrew_ipa_node",
                tags=["phonemization", "ipa", "hebrew"],
            ),
        ]
    )
