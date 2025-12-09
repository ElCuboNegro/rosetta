"""Data quality validation script.

This script validates the quality and reliability of aligned data
before using it as a baseline for testing.
"""

import pandas as pd
import json
from pathlib import Path
import sys

# Fix console encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def validate_enriched_entries():
    """Validate the quality of enriched entries."""
    print("=" * 80)
    print("DATA QUALITY VALIDATION REPORT")
    print("=" * 80)

    # Load data
    enriched_path = Path("data/03_primary/enriched_entries.parquet")
    if not enriched_path.exists():
        print("ERROR: Enriched entries not found. Run pipeline first.")
        return False

    df = pd.read_parquet(enriched_path)

    print(f"\n1. BASIC STATISTICS")
    print(f"   Total aligned entries: {len(df):,}")

    # Match type distribution
    if "match_type" in df.columns:
        print(f"\n2. MATCH TYPE DISTRIBUTION")
        for match_type, count in df["match_type"].value_counts().items():
            percentage = (count / len(df)) * 100
            print(f"   {match_type}: {count:,} ({percentage:.1f}%)")

    # Check for missing data
    print(f"\n3. DATA COMPLETENESS")
    required_fields = ["es_word", "he_word", "es_ipa", "he_ipa", "es_definition"]
    for field in required_fields:
        if field in df.columns:
            missing = df[field].isna().sum()
            empty = (df[field] == "").sum() if df[field].dtype == object else 0
            total_missing = missing + empty
            percentage = (total_missing / len(df)) * 100
            status = "✓" if percentage < 5 else "⚠" if percentage < 20 else "✗"
            print(f"   {status} {field}: {total_missing:,} missing ({percentage:.1f}%)")

    # Validate Hebrew IPA coverage
    print(f"\n4. HEBREW IPA COVERAGE")
    if "he_ipa" in df.columns:
        valid_ipa = df[
            (df["he_ipa"].notna()) &
            (df["he_ipa"] != "") &
            (df["he_ipa"].str.len() > 2)
        ]
        coverage = (len(valid_ipa) / len(df)) * 100
        status = "✓" if coverage >= 80 else "⚠" if coverage >= 50 else "✗"
        print(f"   {status} Valid IPA: {len(valid_ipa):,}/{len(df):,} ({coverage:.1f}%)")

        # Check IPA format
        if len(valid_ipa) > 0:
            with_slashes = valid_ipa["he_ipa"].str.startswith("/").sum()
            format_percentage = (with_slashes / len(valid_ipa)) * 100
            print(f"   IPA format (with slashes): {with_slashes:,}/{len(valid_ipa):,} ({format_percentage:.1f}%)")

    # Check for duplicates
    print(f"\n5. DATA INTEGRITY")
    if "es_word" in df.columns and "he_word" in df.columns:
        duplicates = df.duplicated(subset=["es_word", "he_word", "sense_id"], keep=False)
        dup_count = duplicates.sum()
        status = "✓" if dup_count == 0 else "⚠"
        print(f"   {status} Duplicate alignments: {dup_count:,}")

    # Polysemy analysis
    if "es_word" in df.columns:
        polysemic = df.groupby("es_word").size()
        polysemic_words = (polysemic > 1).sum()
        max_senses = polysemic.max()
        avg_senses = polysemic.mean()
        print(f"\n6. POLYSEMY ANALYSIS")
        print(f"   Polysemic words: {polysemic_words:,}")
        print(f"   Max senses per word: {max_senses}")
        print(f"   Avg senses per word: {avg_senses:.2f}")

    # Sample quality check
    print(f"\n7. SAMPLE DATA (First 5 entries)")
    print("   " + "-" * 76)
    sample = df.head(5)
    for idx, row in sample.iterrows():
        es_word = row.get("es_word", "N/A")
        he_word = row.get("he_word", "N/A")
        match_type = row.get("match_type", "N/A")
        he_ipa = row.get("he_ipa", "N/A")

        print(f"   {es_word} → {he_word}")
        print(f"      Match: {match_type}, IPA: {he_ipa}")

    # Overall assessment
    print(f"\n8. OVERALL ASSESSMENT")

    issues = []

    # Check critical metrics
    if "match_type" in df.columns:
        direct_percentage = (df["match_type"] == "direct").sum() / len(df) * 100
        if direct_percentage < 50:
            issues.append(f"Low direct match rate: {direct_percentage:.1f}%")

    if "he_ipa" in df.columns:
        valid_ipa = df[
            (df["he_ipa"].notna()) &
            (df["he_ipa"] != "") &
            (df["he_ipa"].str.len() > 2)
        ]
        ipa_coverage = (len(valid_ipa) / len(df)) * 100
        if ipa_coverage < 80:
            issues.append(f"Low IPA coverage: {ipa_coverage:.1f}%")

    for field in ["es_word", "he_word"]:
        if field in df.columns:
            missing = df[field].isna().sum() + (df[field] == "").sum()
            if missing > len(df) * 0.05:
                issues.append(f"Missing {field}: {missing:,} entries")

    if issues:
        print("   ⚠ ISSUES FOUND:")
        for issue in issues:
            print(f"      - {issue}")
        print("\n   RECOMMENDATION: Address issues before using as baseline")
        return False
    else:
        print("   ✓ DATA QUALITY: GOOD")
        print("   Data is reliable for use as validation baseline")
        return True


def validate_dictionary_output():
    """Validate the final dictionary output."""
    print("\n" + "=" * 80)
    print("DICTIONARY OUTPUT VALIDATION")
    print("=" * 80)

    dict_path = Path("data/08_reporting/dictionary_v1.json")
    if not dict_path.exists():
        print("ERROR: Dictionary not found.")
        return False

    try:
        with open(dict_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON - {e}")
        return False

    if "entries" not in data:
        print("ERROR: No entries in dictionary")
        return False

    entries = data["entries"]
    print(f"\n   Total entries: {len(entries):,}")

    # Count senses
    total_senses = sum(len(e["entry"]["senses"]) for e in entries)
    print(f"   Total senses: {total_senses:,}")
    print(f"   Avg senses/entry: {total_senses/len(entries):.2f}")

    # IPA coverage
    senses_with_ipa = sum(
        1 for e in entries
        for s in e["entry"]["senses"]
        if s.get("ipa_hebrew") and s["ipa_hebrew"] not in ["", "None"]
    )

    ipa_coverage = (senses_with_ipa / total_senses) * 100 if total_senses > 0 else 0
    status = "✓" if ipa_coverage >= 80 else "⚠"
    print(f"   {status} Hebrew IPA coverage: {ipa_coverage:.1f}%")

    return True


if __name__ == "__main__":
    enriched_valid = validate_enriched_entries()
    dict_valid = validate_dictionary_output()

    print("\n" + "=" * 80)
    if enriched_valid and dict_valid:
        print("✓ ALL VALIDATIONS PASSED")
        print("Data is reliable for production use and testing.")
    else:
        print("⚠ VALIDATIONS FAILED")
        print("Review issues above before proceeding to production.")
    print("=" * 80)
