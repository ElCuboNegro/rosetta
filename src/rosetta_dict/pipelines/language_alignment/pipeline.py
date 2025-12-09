"""Language alignment pipeline for matching Spanish-Hebrew entries."""

from kedro.pipeline import Pipeline, node

from .nodes import align_languages, cluster_polysemic_senses, enrich_entries, structure_senses


def create_pipeline(**kwargs) -> Pipeline:
    """Create the language alignment pipeline.

    This pipeline aligns Spanish and Hebrew word entries using multiple strategies
    (direct translations, triangulation, fuzzy matching), enriches them with
    example sentences, and structures them into polysemic senses.

    Returns:
        Pipeline with alignment and structuring nodes.
    """
    return Pipeline(
        [
            node(
                func=align_languages,
                inputs={
                    "spanish_df": "raw_spanish_entries",
                    "hebrew_df": "raw_hebrew_entries",
                    "bridge_df": "bridge_entries"
                },
                outputs="aligned_matches",
                name="align_languages_node",
                tags=["alignment", "matching", "core"],
            ),
            node(
                func=enrich_entries,
                inputs=["aligned_matches", "clean_examples"],
                outputs="enriched_entries_raw",
                name="enrich_entries_node",
                tags=["alignment", "enrichment", "examples"],
            ),
            node(
                func=cluster_polysemic_senses,
                inputs="enriched_entries_raw",
                outputs="enriched_entries",
                name="cluster_polysemic_senses_node",
                tags=["alignment", "clustering", "polysemy"],
            ),
            node(
                func=structure_senses,
                inputs="enriched_entries",
                outputs="aligned_dictionary",
                name="structure_senses_node",
                tags=["alignment", "structuring", "output"],
            ),
        ]
    )
