import pandas as pd
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_false_positives():
    try:
        # Load the aligned catalog
        df = pd.read_parquet("data/01_raw/aligned_catalogs.parquet")

        # Check specifically for Mani (Hebron) vs Samaniego (Fables)
        # Mani IDs in Ben Yehuda: 42115, 42389, 42399 (from user report)
        # Samaniego ID: 55206

        mani_ids = ["42115", "42389", "42399"]
        samaniego_id = "55206"

        print(f"Total Matches: {len(df)}")

        false_positives = df[df["benyehuda_id"].astype(str).isin(mani_ids)]

        if not false_positives.empty:
            print("\nWARNING: FOUND SUSPICIOUS MATCHES FOR MANI:")
            print(
                false_positives[
                    ["benyehuda_id", "he_title", "gutenberg_id", "match_title", "author_filtered"]
                ]
            )

            # Check if they match Samaniego
            samaniego_matches = false_positives[
                false_positives["gutenberg_id"].astype(str) == samaniego_id
            ]
            if not samaniego_matches.empty:
                print("\nCRITICAL: Mani still matches Samaniego (55206)!")
            else:
                print("\nMani matches found, but not to Samaniego (Good).")
        else:
            print(
                "\nSUCCESS: No matches found for Mani's specific IDs (42115, etc). Strict filtering worked."
            )

        # Check for any match to Samaniego
        sam_matches = df[df["gutenberg_id"].astype(str) == samaniego_id]
        if not sam_matches.empty:
            print(f"\nMatches for Samaniego (55206): {len(sam_matches)}")
            print(sam_matches[["benyehuda_id", "he_title"]])
        else:
            print("\nNo matches for Samaniego (expected if no Hebrew translation exists).")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    check_false_positives()
