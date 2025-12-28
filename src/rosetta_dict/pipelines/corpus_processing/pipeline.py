"""
This is a boilerplate pipeline 'corpus_processing'
generated using Kedro 0.19.1
"""

from kedro.pipeline import Pipeline, pipeline, node
from .nodes import process_wiktionary_examples, process_tatoeba_sentences


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=process_wiktionary_examples,
                inputs="raw_spanish_entries_unfiltered",
                outputs="wiktionary_examples_tagged",
                name="process_wiktionary_examples_node",
            ),
            node(
                func=process_tatoeba_sentences,
                inputs="clean_examples",
                outputs="tatoeba_examples_tagged",
                name="process_tatoeba_sentences_node",
            ),
        ]
    )
