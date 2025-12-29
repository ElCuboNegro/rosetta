import pandas as pd
import torch
import numpy as np
import logging
from sentence_transformers import SentenceTransformer, util

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test():
    # Load model
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

    t1 = "דון קישוט איש למנשא"
    t2 = "Don Quijote"
    t3 = "Don Quijote de la Mancha"
    t4 = "Don Quijote (Don Quixote)"

    embs = model.encode([t1, t2, t3, t4], convert_to_tensor=True)

    scores = util.cos_sim(embs[0:1], embs[1:])

    logger.info(f"Similarity scores for '{t1}':")
    logger.info(f"  vs '{t2}': {scores[0][0].item():.4f}")
    logger.info(f"  vs '{t3}': {scores[0][1].item():.4f}")
    logger.info(f"  vs '{t4}': {scores[0][2].item():.4f}")

    # Check if ID 2000 is in gutenberg_catalog
    gutenberg = pd.read_parquet("data/01_raw/gutenberg_catalog.parquet")
    dq_es = gutenberg[gutenberg["gutenberg_id"] == 2000]
    if not dq_es.empty:
        logger.info(
            f"ID 2000 found in catalog: {dq_es.iloc[0]['title']} (Lang: {dq_es.iloc[0]['language']})"
        )
    else:
        logger.warning("ID 2000 NOT found in gutenberg_catalog.parquet")


if __name__ == "__main__":
    test()
