import pandas as pd
import logging


def verify_validation():
    print("--- Verifying Aligned Matches Validation ---")

    try:
        # Load the aligned matches (which should now exist)
        df = pd.read_parquet("data/03_primary/aligned_matches.parquet")
        print(f"Aligned Matches Count: {len(df)}")

        if len(df) == 0:
            print("ERROR: Aligned matches matches is still empty!")
            return

        print("Sample Entry:")
        print(df.iloc[0])

        # Check required fields
        required_fields = [
            "es_word",
            "es_ipa",
            "es_pos",
            "es_definition",
            "he_word",
            "he_ipa",
            "sense_id",
            "match_type",
            "confidence",
        ]
        missing = [f for f in required_fields if f not in df.columns]

        if missing:
            print(f"ERROR: Missing fields: {missing}")
        else:
            print("All required fields are present.")

    except Exception as e:
        print(f"Error reading aligned matches: {e}")


if __name__ == "__main__":
    verify_validation()
