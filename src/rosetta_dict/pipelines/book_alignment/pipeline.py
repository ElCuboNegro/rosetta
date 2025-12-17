from kedro.pipeline import Pipeline, pipeline, node
from .nodes import align_books


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=align_books,
                inputs="gutenberg_files_list",
                outputs="aligned_book_sentences",
                name="align_books_node",
            ),
        ]
    )
