"""Build Hebrew IPA lookup table from Wiktionary data.

This script extracts Hebrew words with their IPA pronunciations from Wiktionary
and generates a Python dictionary for use in the IPA generator.
"""

import sys

sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path

import pandas as pd


def build_lookup_table():
    """Build IPA lookup table from Wiktionary data."""

    print("Building Hebrew IPA lookup table from Wiktionary data...")

    # Load Hebrew reference data
    data_path = Path("data/02_intermediate/raw_hebrew_entries.parquet")
    if not data_path.exists():
        print(f"ERROR: Data not found at {data_path}")
        return

    df = pd.read_parquet(data_path)

    # Get Hebrew words with IPA
    hebrew_data = df[["word", "ipa"]].drop_duplicates()
    hebrew_data = hebrew_data[
        (hebrew_data["word"].notna()) &
        (hebrew_data["word"] != "") &
        (hebrew_data["ipa"].notna()) &
        (hebrew_data["ipa"] != "") &
        (hebrew_data["ipa"].str.len() > 2)
    ]

    print(f"Total Hebrew words with IPA: {len(hebrew_data)}")

    # Clean IPA (remove brackets, extra notation)
    def clean_ipa(ipa_str):
        """Clean IPA string for lookup table."""
        if not ipa_str:
            return None

        import re

        # Remove slashes and brackets first
        ipa = ipa_str.strip().strip('/[]')

        # Remove bracketed alternatives like [ħɔːˈθuːl]
        if '[' in ipa:
            ipa = ipa.split('[')[0].strip()

        # Remove alternative notations like ~ /ʔarsˤ/
        if '~' in ipa:
            ipa = ipa.split('~')[0].strip()

        # Remove optional parts like (h), (ʔ), or (ʕ)
        ipa = re.sub(r'\([^)]*\)', '', ipa)

        # Remove any remaining slashes or brackets
        ipa = ipa.strip('/ []')

        # Clean up extra spaces
        ipa = re.sub(r'\s+', ' ', ipa).strip()

        return ipa if ipa else None

    # Build lookup dictionary
    lookup_table = {}
    for _, row in hebrew_data.iterrows():
        hebrew = row["word"]
        ipa = clean_ipa(row["ipa"])

        if ipa and hebrew:
            # Add ALL entries including multi-word phrases
            # This significantly improves coverage for common phrases
            lookup_table[hebrew] = ipa

    print(f"Built lookup table with {len(lookup_table)} entries")

    # Sort by word for readability
    sorted_items = sorted(lookup_table.items(), key=lambda x: x[0])

    # Generate Python code
    print("\n" + "="*80)
    print("PYTHON CODE FOR LOOKUP TABLE")
    print("="*80)
    print("\nCOMMON_WORD_IPA = {")

    for hebrew, ipa in sorted_items[:500]:  # Limit to first 500 for now
        # Escape single quotes in IPA if any
        ipa_escaped = ipa.replace("'", "\\'")
        print(f"    '{hebrew}': '{ipa_escaped}',")

    print("}")

    print(f"\n\nTotal entries: {len(sorted_items)}")
    print(f"Exported: {min(500, len(sorted_items))}")

    # Save to file
    output_file = Path("src/rosetta_dict/pipelines/phonemization/hebrew_ipa_lookup.py")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('"""Hebrew IPA lookup table extracted from Wiktionary."""\n\n')
        f.write('COMMON_WORD_IPA = {\n')

        for hebrew, ipa in sorted_items:
            ipa_escaped = ipa.replace("'", "\\'")
            f.write(f"    '{hebrew}': '{ipa_escaped}',\n")

        f.write('}\n')

    print(f"\nLookup table saved to {output_file}")


if __name__ == "__main__":
    build_lookup_table()
