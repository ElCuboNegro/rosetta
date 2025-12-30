import logging
import pandas as pd
import spacy
from spacy.cli import download

logger = logging.getLogger(__name__)


def _ensure_spacy_model(model_name: str = "es_core_news_sm"):
    """Ensure Spacy model is downloaded."""
    try:
        spacy.load(model_name)
    except OSError:
        logger.info(f"Downloading Spacy model: {model_name}")
        download(model_name)


def process_wiktionary_examples(entries_df: pd.DataFrame) -> pd.DataFrame:
    """
    Process Wiktionary examples to extract linguistic features.

    Args:
        entries_df: DataFrame containing 'word', 'examples' (list of strs).

    Returns:
        DataFrame with exploded examples and linguistic tags.
    """
    _ensure_spacy_model("es_core_news_sm")
    nlp = spacy.load("es_core_news_sm", disable=["ner"])

    # 1. Explode examples (one row per example sentence)
    examples_df = entries_df[["word", "examples"]].explode("examples").dropna()
    examples_df = examples_df[examples_df["examples"].str.len() > 5]  # Filter too short garbage

    # 2. Process with Spacy (Batch processing for speed)
    # Using nlp.pipe which is much faster than applying row-by-row
    texts = examples_df["examples"].tolist()
    docs = list(nlp.pipe(texts, batch_size=50))

    # 3. Extract features
    processed_data = []

    for (idx, row), doc in zip(examples_df.iterrows(), docs):
        tokens = [token.text for token in doc]
        pos_tags = [token.pos_ for token in doc]
        dependencies = [(token.text, token.dep_, token.head.text) for token in doc]

        processed_data.append(
            {
                "source_word": row["word"],
                "example_text": row["examples"],
                "tokens": tokens,
                "pos_tags": pos_tags,
                "dependencies": dependencies,
            }
        )

    logger.info(f"Processed {len(processed_data)} Wiktionary examples.")
    df = pd.DataFrame(processed_data)
    if not df.empty:
        df.reset_index(inplace=True)
        df.rename(columns={"index": "id"}, inplace=True)
    return df


def process_tatoeba_sentences(clean_examples_df: pd.DataFrame) -> pd.DataFrame:
    """
    Process Tatoeba sentences for usage examples.

    Args:
        clean_examples_df: DataFrame with 'es', 'he' columns.

    Returns:
        Annotated DataFrame.
    """
    _ensure_spacy_model("es_core_news_sm")
    nlp = spacy.load("es_core_news_sm", disable=["ner"])

    # Filter for Spanish sentences
    texts = clean_examples_df["es"].tolist()
    docs = list(nlp.pipe(texts, batch_size=50))

    processed_data = []
    for (idx, row), doc in zip(clean_examples_df.iterrows(), docs):
        tokens = [token.text for token in doc]
        pos_tags = [token.pos_ for token in doc]

        processed_data.append(
            {
                "source_es": row["es"],
                "target_he": row["he"],
                "es_tokens": tokens,
                "es_pos_tags": pos_tags,
            }
        )

    logger.info(f"Processed {len(processed_data)} Tatoeba sentences.")
    df = pd.DataFrame(processed_data)
    if not df.empty:
        df.reset_index(inplace=True)
        df.rename(columns={"index": "id"}, inplace=True)
    return df
