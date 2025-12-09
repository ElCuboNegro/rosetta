"""Data validation pipeline."""

from kedro.pipeline import Pipeline, node

from .nodes import (
    generate_data_quality_report,
    validate_aligned_matches,
    validate_enriched_entries,
    validate_wiktionary_entries,
)


def create_pipeline(**kwargs) -> Pipeline:
    """Create the data validation pipeline.

    This pipeline validates data quality at each stage of processing.
    """
    return Pipeline(
        [
            # Validate parsed Wiktionary entries
            node(
                func=lambda df: validate_wiktionary_entries(df, "es"),
                inputs="raw_spanish_entries",
                outputs="validated_spanish_entries",
                name="validate_spanish_entries",
            ),
            node(
                func=lambda df: validate_wiktionary_entries(df, "he"),
                inputs="raw_hebrew_entries",
                outputs="validated_hebrew_entries",
                name="validate_hebrew_entries",
            ),
            # Validate aligned matches
            node(
                func=validate_aligned_matches,
                inputs="language_alignment.aligned_matches",
                outputs="validated_aligned_matches",
                name="validate_aligned_matches",
            ),
            # Validate enriched entries
            node(
                func=validate_enriched_entries,
                inputs="language_alignment.enriched_entries",
                outputs="validated_enriched_entries",
                name="validate_enriched_entries",
            ),
            # Generate data quality report
            node(
                func=generate_data_quality_report,
                inputs="validated_enriched_entries",
                outputs="data_quality_report",
                name="generate_quality_report",
            ),
        ]
    )
