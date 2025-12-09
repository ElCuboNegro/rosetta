import pandas as pd
import logging
import numpy as np


def debug_map():
    print("--- Debugging Triangulation Map ---")

    try:
        bridge_df = pd.read_parquet("data/02_intermediate/bridge_entries.parquet")
        es_df = pd.read_parquet("data/02_intermediate/raw_spanish_entries.parquet")
        he_df = pd.read_parquet("data/02_intermediate/raw_hebrew_entries.parquet")

        print(f"Loaded: Bridge {len(bridge_df)}, ES {len(es_df)}, HE {len(he_df)}")

        # Replicate Map Building
        es_to_he_map = {}
        for i, (idx, row) in enumerate(bridge_df.iterrows()):
            if i == 0:
                print(f"Type of translations_es: {type(row['translations_es'])}")
                print(f"Value: {row['translations_es']}")

            # Robust conversion to list

            val_es = row["translations_es"]
            if isinstance(val_es, np.ndarray):
                es_trans = val_es.tolist()
            elif isinstance(val_es, list):
                es_trans = val_es
            else:
                es_trans = []

            val_he = row["translations_he"]
            if isinstance(val_he, np.ndarray):
                he_trans = val_he.tolist()
            elif isinstance(val_he, list):
                he_trans = val_he
            else:
                he_trans = []

            if es_trans and he_trans:
                for es_word in es_trans:
                    if es_word not in es_to_he_map:
                        es_to_he_map[es_word] = set()
                    for he_word in he_trans:
                        es_to_he_map[es_word].add(he_word)

        print(f"Map size: {len(es_to_he_map)}")
        sample_keys = list(es_to_he_map.keys())[:5]
        print(f"Sample keys in map: {sample_keys}")

        # Check intersection with Spanish Data
        es_vocab = set(es_df["word"].values)
        intersection = es_vocab.intersection(set(es_to_he_map.keys()))
        print(f"Overlap between Spanish Vocab and Map Keys: {len(intersection)}")

        if len(intersection) == 0:
            print("CRITICAL: No Spanish words match the bridge keys!")
            print(f"Sample ES Vocab: {list(es_vocab)[:5]}")
            return

        # Check Hebrew Lookup
        he_vocab = set(he_df["word"].values)
        print(f"Hebrew Vocab Size: {len(he_vocab)}")

        hits = 0
        for es_word in list(intersection)[:100]:
            candidates = es_to_he_map[es_word]
            found = False
            for cand in candidates:
                if cand in he_vocab:
                    hits += 1
                    found = True
                    print(f"MATCH: {es_word} -> {cand}")
            if not found:
                print(f"MISS: {es_word} -> Candidates {candidates} (Not in HE vocab)")

        print(f"Total Hits in sample: {hits}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    debug_map()
