import pandas as pd
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def debug_alignment():
    print("--- Debugging Alignment Logic ---")

    # Load Dataframes
    try:
        print("Loading dataframes...")
        es_df = pd.read_parquet("data/02_intermediate/raw_spanish_entries.parquet")
        he_df = pd.read_parquet("data/02_intermediate/raw_hebrew_entries.parquet")
        bridge_df = pd.read_parquet("data/02_intermediate/bridge_entries.parquet")

        print(f"Loaded: Spanish {len(es_df)}, Hebrew {len(he_df)}, Bridge {len(bridge_df)}")
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    # 1. Debug Direct Alignment
    print("\n--- 1. Direct Alignment Debug ---")
    # count entries with non-empty translations_he

    # Handle both list and other types
    def get_len(x):
        if isinstance(x, list):
            return len(x)
        return 0

    es_with_he = es_df[es_df["translations_he"].apply(lambda x: get_len(x) > 0)]
    print(f"Spanish entries with Hebrew translations: {len(es_with_he)}/{len(es_df)}")

    if not es_with_he.empty:
        sample = es_with_he.iloc[0]
        print(f"Sample Entry: Word='{sample['word']}'")
        print(f"Translations: {sample['translations_he']}")

        # Check if these translations exist in Hebrew DF
        for t in sample["translations_he"]:
            match = he_df[he_df["word"] == t]
            print(f"Translation '{t}' found in Hebrew dictionary? {not match.empty}")
            if not match.empty:
                print("  Match found! Direct alignment should work for this.")
            else:
                # Check for near matches or validation issues
                print("  No match in Hebrew DF.")
                # Check if hebrew df has words around it?

    # 2. Debug Triangulation
    print("\n--- 2. Triangulation Debug ---")
    print("Bridge DataFrame Source Languages:")
    print(bridge_df["source_lang"].value_counts())

    es_bridge = bridge_df[bridge_df["source_lang"] == "es"]
    print(f"Entries with source_lang='es' in bridge: {len(es_bridge)}")

    # Check if English entries map to Spanish words
    en_bridge = bridge_df[bridge_df["source_lang"] == "en"]

    # Find an English entry that translates to Spanish
    # We want to see if we can link Spanish Word -> English Entry -> Hebrew Translation

    found_link = False
    for i, row in en_bridge.head(100).iterrows():
        # Check translations_es
        es_trans = row.get("translations_es", [])
        he_trans = row.get("translations_he", [])

        if es_trans and he_trans:
            print(f"\nPotential Bridge Link found in English word '{row['word']}':")
            print(f"  - Spanish: {es_trans}")
            print(f"  - Hebrew: {he_trans}")

            # Use 'code' if it's a dict, or string
            # In parsed data, translations are usually dicts or strings depending on parser
            # Let's inspect one structure
            print(f"  - Trans structure: {type(es_trans[0])} - {es_trans[0]}")
            found_link = True
            break

    if not found_link:
        print("\nNo entries found in first 100 English rows with both ES and HE translations.")


if __name__ == "__main__":
    debug_alignment()
