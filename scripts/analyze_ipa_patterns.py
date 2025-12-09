"""Analyze IPA generation patterns to improve algorithm.

This script analyzes the differences between Wiktionary IPA and our generated IPA
to identify patterns and improve the generation algorithm.
"""

import sys

sys.stdout.reconfigure(encoding='utf-8')

from collections import Counter
from pathlib import Path

import pandas as pd

from rosetta_dict.pipelines.phonemization.hebrew_ipa_generator import HebrewIPAGenerator


def analyze_ipa_patterns():
    """Analyze patterns in IPA generation."""

    print("="*80)
    print("HEBREW IPA PATTERN ANALYSIS")
    print("="*80)

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

    print(f"\nTotal Hebrew words with IPA: {len(hebrew_data)}")

    # Sample for analysis
    sample = hebrew_data.head(20)

    print("\n" + "="*80)
    print("SAMPLE WIKTIONARY IPA (First 20 words)")
    print("="*80)

    for idx, row in sample.iterrows():
        hebrew = row["word"]
        wikt_ipa = row["ipa"]
        print(f"\nHebrew: {hebrew}")
        print(f"  Wiktionary IPA: {wikt_ipa}")

    # Analyze IPA character patterns
    print("\n" + "="*80)
    print("IPA CHARACTER ANALYSIS")
    print("="*80)

    # Collect all IPA characters
    all_ipa_chars = Counter()
    for ipa in hebrew_data["ipa"]:
        # Remove slashes and spaces
        ipa_clean = ipa.strip("/").strip()
        for char in ipa_clean:
            if char not in [" ", "-", ".", "ˈ", "ˌ"]:  # Ignore separators
                all_ipa_chars[char] += 1

    print("\nMost common IPA characters in Wiktionary data:")
    for char, count in all_ipa_chars.most_common(30):
        print(f"  {char}: {count}")

    # Test our generator
    print("\n" + "="*80)
    print("COMPARING OUR GENERATION vs WIKTIONARY")
    print("="*80)

    generator = HebrewIPAGenerator(variant="modern", use_phonikud=True, fallback_to_rules=True)

    examples = []
    for idx, row in hebrew_data.head(50).iterrows():
        hebrew = row["word"]
        wikt_ipa = row["ipa"]

        # Generate with our algorithm
        generated_ipa = generator.generate_ipa(hebrew)

        # Check similarity
        if generated_ipa:
            gen_clean = generated_ipa.strip("/").strip()
            wikt_clean = wikt_ipa.strip("/").strip()

            # Simple character overlap
            common = sum(1 for c in gen_clean if c in wikt_clean)
            similarity = common / max(len(gen_clean), len(wikt_clean)) if max(len(gen_clean), len(wikt_clean)) > 0 else 0

            examples.append({
                "hebrew": hebrew,
                "wiktionary": wikt_ipa,
                "generated": generated_ipa,
                "similarity": similarity
            })

    # Show best matches
    examples_sorted = sorted(examples, key=lambda x: x["similarity"], reverse=True)

    print("\nTOP 10 BEST MATCHES:")
    for i, ex in enumerate(examples_sorted[:10], 1):
        print(f"\n{i}. {ex['hebrew']}")
        print(f"   Wiktionary: {ex['wiktionary']}")
        print(f"   Generated:  {ex['generated']}")
        print(f"   Similarity: {ex['similarity']:.1%}")

    print("\nTOP 10 WORST MATCHES:")
    for i, ex in enumerate(examples_sorted[-10:], 1):
        print(f"\n{i}. {ex['hebrew']}")
        print(f"   Wiktionary: {ex['wiktionary']}")
        print(f"   Generated:  {ex['generated']}")
        print(f"   Similarity: {ex['similarity']:.1%}")

    # Analyze patterns
    print("\n" + "="*80)
    print("PATTERN ANALYSIS")
    print("="*80)

    # Check if phonikud is working
    print("\nChecking phonikud library status...")
    try:
        from phonikud import phonemize
        test_word = "שלום"
        result = phonemize(test_word)
        print("✓ phonikud is available")
        print(f"  Test: {test_word} → {result}")
    except ImportError:
        print("✗ phonikud library NOT available")
        print("  Install with: pip install phonikud phonikud-onnx")
    except Exception as e:
        print(f"⚠ phonikud error: {e}")

    # Identify common differences
    print("\nCommon differences:")

    # Collect character mappings that differ
    char_mismatches = Counter()
    for ex in examples:
        wikt = ex["wiktionary"].strip("/")
        gen = ex["generated"].strip("/")

        # Very simple: check what characters are in wikt but not in generated
        wikt_chars = set(wikt)
        gen_chars = set(gen)

        missing_in_gen = wikt_chars - gen_chars
        for char in missing_in_gen:
            char_mismatches[char] += 1

    print("\nCharacters in Wiktionary but often missing in our generation:")
    for char, count in char_mismatches.most_common(20):
        print(f"  {char}: missing in {count} cases")

    # Summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)

    exact_matches = sum(1 for ex in examples if ex["similarity"] == 1.0)
    high_similarity = sum(1 for ex in examples if ex["similarity"] >= 0.7)
    medium_similarity = sum(1 for ex in examples if ex["similarity"] >= 0.5)

    print(f"\nTotal words tested: {len(examples)}")
    print(f"Exact matches (100%): {exact_matches} ({exact_matches/len(examples)*100:.1f}%)")
    print(f"High similarity (>=70%): {high_similarity} ({high_similarity/len(examples)*100:.1f}%)")
    print(f"Medium similarity (>=50%): {medium_similarity} ({medium_similarity/len(examples)*100:.1f}%)")
    print(f"Average similarity: {sum(ex['similarity'] for ex in examples)/len(examples)*100:.1f}%")


if __name__ == "__main__":
    analyze_ipa_patterns()
