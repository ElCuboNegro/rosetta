"""Test script for Hebrew IPA generator using existing dictionary data."""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from rosetta_dict.pipelines.reporting.hebrew_ipa_generator import HebrewIPAGenerator


def load_test_data(dict_path: str, limit: int = 50):
    """Load existing IPA data from dictionary for testing.
    
    Args:
        dict_path: Path to dictionary_v1.json
        limit: Maximum number of test cases to extract
        
    Returns:
        List of (hebrew_word, existing_ipa) tuples
    """
    with open(dict_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    test_cases = []

    for entry_dict in data.get("entries", []):
        entry = entry_dict.get("entry", {})
        senses = entry.get("senses", [])

        for sense in senses:
            hebrew = sense.get("hebrew", "")
            ipa_hebrew = sense.get("ipa_hebrew", "")

            # Only use entries that have existing IPA
            if hebrew and ipa_hebrew:
                test_cases.append((hebrew, ipa_hebrew))

                if len(test_cases) >= limit:
                    return test_cases

    return test_cases


def run_validation_tests():
    """Run validation tests using existing dictionary data."""

    print("=" * 80)
    print("Hebrew IPA Generator - Validation Test")
    print("=" * 80)
    print()

    # Load test data
    dict_path = "data/08_reporting/dictionary_v1.json"
    print(f"Loading test data from {dict_path}...")

    test_cases = load_test_data(dict_path, limit=50)
    print(f"Loaded {len(test_cases)} test cases with existing IPA\n")

    if not test_cases:
        print("ERROR: No test cases found with existing IPA!")
        return

    # Test with Modern Israeli Hebrew
    print("-" * 80)
    print("Testing: Modern Israeli Hebrew")
    print("-" * 80)

    generator = HebrewIPAGenerator(variant="modern", use_phonikud=True, fallback_to_rules=True)

    results = []
    for hebrew, existing_ipa in test_cases:
        result = generator.test_against_existing(hebrew, existing_ipa)
        results.append(result)

    # Calculate statistics
    exact_matches = sum(1 for r in results if r["exact_match"])
    avg_similarity = sum(r["similarity"] for r in results) / len(results) if results else 0
    phonikud_used = sum(1 for r in results if r["method"] == "phonikud")
    rules_used = sum(1 for r in results if r["method"] == "rules")

    print("\nResults:")
    print(f"  Total tests: {len(results)}")
    print(f"  Exact matches: {exact_matches} ({100*exact_matches/len(results):.1f}%)")
    print(f"  Average similarity: {avg_similarity:.2f}")
    print(f"  Method used: phonikud={phonikud_used}, rules={rules_used}")
    print()

    # Show sample comparisons
    print("Sample comparisons (first 10):")
    print("-" * 80)
    print(f"{'Hebrew':<15} {'Existing IPA':<25} {'Generated IPA':<25} {'Match':<8}")
    print("-" * 80)

    for i, result in enumerate(results[:10]):
        hebrew = result["hebrew"]
        existing = result["existing_ipa"]
        generated = result["generated_ipa"] or "(failed)"
        match = "✓" if result["exact_match"] else f"{result['similarity']:.2f}"

        print(f"{hebrew:<15} {existing:<25} {generated:<25} {match:<8}")

    print()

    # Show failures
    failures = [r for r in results if not r["generated_ipa"]]
    if failures:
        print(f"\nFailed to generate ({len(failures)} cases):")
        print("-" * 80)
        for r in failures[:5]:  # Show first 5 failures
            print(f"  {r['hebrew']:<15} (expected: {r['existing_ipa']})")
        if len(failures) > 5:
            print(f"  ... and {len(failures) - 5} more")

    print()
    print("=" * 80)
    print("Test Complete")
    print("=" * 80)

    return results


if __name__ == "__main__":
    results = run_validation_tests()
