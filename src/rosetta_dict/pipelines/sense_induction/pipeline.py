from kedro.pipeline import Pipeline, pipeline, node
from .nodes import induce_senses


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=induce_senses,
                inputs=[
                    "wiktionary_examples_tagged",
                    "aligned_book_sentences",
                    "params:sense_induction_params",
                ],
                outputs="induced_senses_clusters",
                name="induce_senses_node",
            ),
        ]
    )
