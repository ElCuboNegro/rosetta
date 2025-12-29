from kedro.pipeline import Pipeline, node
from .nodes import align_catalogs_bert, enrich_benyehuda_with_wikidata


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            node(
                func=enrich_benyehuda_with_wikidata,
                inputs="benyehuda_catalog_raw",
                outputs="benyehuda_catalog_enriched",
                name="enrich_benyehuda_with_wikidata_node",
            ),
            node(
                func=align_catalogs_bert,
                inputs=[
                    "benyehuda_catalog_enriched",
                    "gutenberg_catalog_raw",
                    "params:alignment_threshold",
                ],
                outputs="aligned_catalogs",
                name="align_catalogs_bert_node",
            ),
        ]
    )
