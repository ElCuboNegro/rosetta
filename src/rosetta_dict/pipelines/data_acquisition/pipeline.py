"""Data acquisition pipeline for downloading raw data sources."""

from kedro.pipeline import Pipeline, node

from .nodes import download_kaikki_data


def create_pipeline(**kwargs) -> Pipeline:
    """Create the data acquisition pipeline.

    This pipeline downloads pre-extracted Wiktionary data from kaikki.org
    for Spanish, Hebrew, English, French, and German editions to enable
    robust multi-point triangulation for translation alignment.

    Returns:
        Pipeline with download nodes for each language.
    """
    return Pipeline(
        [
            node(
                func=download_kaikki_data,
                inputs=["params:kaikki.spanish_lang_code", "params:kaikki.es_data_path"],
                outputs="es_dump_filepath",
                name="download_spanish_kaikki_node",
                tags=["download", "io", "spanish"],
            ),
            node(
                func=download_kaikki_data,
                inputs=["params:kaikki.hebrew_lang_code", "params:kaikki.he_data_path"],
                outputs="he_dump_filepath",
                name="download_hebrew_kaikki_node",
                tags=["download", "io", "hebrew"],
            ),
            node(
                func=download_kaikki_data,
                inputs=["params:kaikki.english_lang_code", "params:kaikki.en_data_path"],
                outputs="en_dump_filepath",
                name="download_english_kaikki_node",
                tags=["download", "io", "english", "bridge"],
            ),
            node(
                func=download_kaikki_data,
                inputs=["params:kaikki.french_lang_code", "params:kaikki.fr_data_path"],
                outputs="fr_dump_filepath",
                name="download_french_kaikki_node",
                tags=["download", "io", "french", "bridge"],
            ),
            node(
                func=download_kaikki_data,
                inputs=["params:kaikki.german_lang_code", "params:kaikki.de_data_path"],
                outputs="de_dump_filepath",
                name="download_german_kaikki_node",
                tags=["download", "io", "german", "bridge"],
            ),
        ]
    )
