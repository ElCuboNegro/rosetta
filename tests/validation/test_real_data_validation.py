"""Validation tests against actual generated Hebrew dictionary data.

These tests validate the quality of the generated dictionary against the
real data produced by the pipeline, ensuring translation accuracy and
data integrity.
"""

import json
import pandas as pd
import pytest
from pathlib import Path
from rosetta_dict.pipelines.phonemization.hebrew_ipa_generator import HebrewIPAGenerator


class TestRealDataValidation:
    """Validate generated dictionary against actual data."""

    @pytest.fixture
    def dictionary_path(self):
        """Path to the generated dictionary."""
        return Path("data/08_reporting/dictionary_v1.json")

    @pytest.fixture
    def dictionary_with_ipa_path(self):
        """Path to the dictionary with IPA."""
        return Path("data/03_primary/aligned_dictionary_with_ipa.json")

    @pytest.fixture
    def enriched_entries_path(self):
        """Path to enriched entries parquet."""
        return Path("data/03_primary/enriched_entries.parquet")

    @pytest.fixture
    def dictionary_data(self, dictionary_path):
        """Load the generated dictionary."""
        if not dictionary_path.exists():
            pytest.skip(f"Dictionary not found at {dictionary_path}. Run pipeline first.")

        with open(dictionary_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @pytest.fixture
    def enriched_df(self, enriched_entries_path):
        """Load enriched entries DataFrame."""
        if not enriched_entries_path.exists():
            pytest.skip(f"Enriched entries not found. Run pipeline first.")

        return pd.read_parquet(enriched_entries_path)

    def test_dictionary_structure(self, dictionary_data):
        """Validate overall dictionary structure."""
        assert "metadata" in dictionary_data, "Missing metadata"
        assert "entries" in dictionary_data, "Missing entries"

        metadata = dictionary_data["metadata"]
        assert "language_direction" in metadata
        assert "version" in metadata
        assert "source" in metadata
        assert "generated_at" in metadata

        # Validate language direction
        assert metadata["language_direction"] in ["es-he", "he-es", "es-he | he-es"]

    def test_all_entries_have_required_fields(self, dictionary_data):
        """Validate all entries have required fields."""
        entries = dictionary_data["entries"]
        assert len(entries) > 0, "Dictionary is empty"

        required_entry_fields = ["id", "entry"]
        required_nested_fields = ["word", "ipa", "language", "senses"]
        required_sense_fields = ["sense_id", "definition", "ipa_hebrew", "hebrew", "pos"]

        for entry in entries:
            # Check top-level fields
            for field in required_entry_fields:
                assert field in entry, f"Missing field: {field}"

            # Check entry nested fields
            for field in required_nested_fields:
                assert field in entry["entry"], f"Missing nested field: {field}"

            # Check senses
            senses = entry["entry"]["senses"]
            assert len(senses) > 0, f"Entry {entry['id']} has no senses"

            for sense in senses:
                for field in required_sense_fields:
                    assert field in sense, f"Missing sense field: {field} in {entry['id']}"

    def test_hebrew_ipa_coverage(self, dictionary_data):
        """Validate Hebrew IPA coverage meets minimum threshold."""
        entries = dictionary_data["entries"]

        total_senses = 0
        senses_with_ipa = 0

        for entry in entries:
            for sense in entry["entry"]["senses"]:
                total_senses += 1
                ipa_hebrew = sense.get("ipa_hebrew", "")

                if ipa_hebrew and ipa_hebrew != "" and ipa_hebrew != "None":
                    senses_with_ipa += 1

        coverage = senses_with_ipa / total_senses if total_senses > 0 else 0

        # Require at least 80% IPA coverage
        assert coverage >= 0.80, (
            f"Hebrew IPA coverage too low: {coverage:.2%} "
            f"({senses_with_ipa}/{total_senses}). "
            "Expected at least 80%."
        )

    def test_hebrew_ipa_format_consistency(self, dictionary_data):
        """Validate all Hebrew IPA entries follow consistent format."""
        entries = dictionary_data["entries"]
        invalid_ipa = []

        for entry in entries:
            for sense in entry["entry"]["senses"]:
                ipa = sense.get("ipa_hebrew", "")

                if ipa and ipa != "" and ipa != "None":
                    # Should be wrapped in slashes
                    if not (ipa.startswith("/") and ipa.endswith("/")):
                        invalid_ipa.append({
                            "word": entry["entry"]["word"],
                            "hebrew": sense["hebrew"],
                            "ipa": ipa,
                            "issue": "Not wrapped in slashes"
                        })

                    # Should have content between slashes
                    if len(ipa) < 3:  # At least "/X/"
                        invalid_ipa.append({
                            "word": entry["entry"]["word"],
                            "hebrew": sense["hebrew"],
                            "ipa": ipa,
                            "issue": "Too short"
                        })

        assert len(invalid_ipa) == 0, (
            f"Found {len(invalid_ipa)} invalid IPA entries:\n" +
            "\n".join(str(x) for x in invalid_ipa[:10])
        )

    def test_hebrew_character_validation(self, dictionary_data):
        """Validate Hebrew words contain only valid Hebrew characters."""
        entries = dictionary_data["entries"]
        invalid_hebrew = []

        # Hebrew Unicode ranges: 0590-05FF (Hebrew block), FB1D-FB4F (Hebrew presentation forms)
        hebrew_ranges = [
            (0x0590, 0x05FF),  # Main Hebrew block
            (0xFB1D, 0xFB4F),  # Hebrew presentation forms
        ]

        def is_hebrew_char(char):
            """Check if character is in Hebrew Unicode range."""
            code = ord(char)
            return any(start <= code <= end for start, end in hebrew_ranges)

        for entry in entries:
            for sense in entry["entry"]["senses"]:
                hebrew = sense.get("hebrew", "")

                if hebrew:
                    # Check if contains at least some Hebrew characters
                    hebrew_chars = [c for c in hebrew if is_hebrew_char(c)]

                    if len(hebrew_chars) == 0:
                        invalid_hebrew.append({
                            "word": entry["entry"]["word"],
                            "hebrew": hebrew,
                            "issue": "No Hebrew characters found"
                        })

        assert len(invalid_hebrew) == 0, (
            f"Found {len(invalid_hebrew)} invalid Hebrew entries:\n" +
            "\n".join(str(x) for x in invalid_hebrew[:10])
        )

    def test_sense_ids_are_valid(self, dictionary_data):
        """Validate sense IDs are sequential and start from 1."""
        entries = dictionary_data["entries"]
        invalid_sense_ids = []

        for entry in entries:
            senses = entry["entry"]["senses"]
            sense_ids = [s["sense_id"] for s in senses]

            # Should start at 1
            if min(sense_ids) < 1:
                invalid_sense_ids.append({
                    "word": entry["entry"]["word"],
                    "sense_ids": sense_ids,
                    "issue": "Sense ID less than 1"
                })

            # Should be unique within entry
            if len(sense_ids) != len(set(sense_ids)):
                invalid_sense_ids.append({
                    "word": entry["entry"]["word"],
                    "sense_ids": sense_ids,
                    "issue": "Duplicate sense IDs"
                })

        assert len(invalid_sense_ids) == 0, (
            f"Found {len(invalid_sense_ids)} entries with invalid sense IDs:\n" +
            "\n".join(str(x) for x in invalid_sense_ids[:10])
        )

    def test_no_missing_translations(self, dictionary_data):
        """Validate all senses have Hebrew translations."""
        entries = dictionary_data["entries"]
        missing_translations = []

        for entry in entries:
            for sense in entry["entry"]["senses"]:
                hebrew = sense.get("hebrew", "")

                if not hebrew or hebrew == "":
                    missing_translations.append({
                        "word": entry["entry"]["word"],
                        "sense_id": sense["sense_id"],
                        "definition": sense.get("definition", "")
                    })

        # Should have very few missing translations
        missing_rate = len(missing_translations) / sum(
            len(e["entry"]["senses"]) for e in entries
        )

        assert missing_rate < 0.05, (
            f"Too many missing translations: {missing_rate:.2%} "
            f"({len(missing_translations)} entries). Expected < 5%."
        )

    def test_polysemy_handling(self, dictionary_data):
        """Validate polysemic words have multiple distinct senses."""
        entries = dictionary_data["entries"]
        polysemic_words = [e for e in entries if len(e["entry"]["senses"]) > 1]

        assert len(polysemic_words) > 0, "No polysemic words found"

        for entry in polysemic_words:
            senses = entry["entry"]["senses"]

            # Should have different Hebrew words or definitions
            hebrew_words = [s["hebrew"] for s in senses]
            definitions = [s["definition"] for s in senses]

            # At least some variation in translations or definitions
            assert len(set(hebrew_words)) > 1 or len(set(definitions)) > 1, (
                f"Polysemic word {entry['entry']['word']} has identical senses"
            )


class TestHebrewIPAAccuracyAgainstRealData:
    """Validate Hebrew IPA generation accuracy against existing dataset."""

    @pytest.fixture
    def enriched_df(self):
        """Load enriched entries DataFrame."""
        path = Path("data/03_primary/enriched_entries.parquet")
        if not path.exists():
            pytest.skip("Enriched entries not found. Run pipeline first.")

        return pd.read_parquet(path)

    @pytest.fixture
    def ipa_generator(self):
        """IPA generator instance."""
        return HebrewIPAGenerator(variant="modern", use_phonikud=True, fallback_to_rules=True)

    def test_validate_existing_hebrew_ipa(self, enriched_df, ipa_generator):
        """Validate IPA generation against existing Hebrew words in dataset."""
        # Get unique Hebrew words with existing IPA
        hebrew_words = enriched_df[["he_word", "he_ipa"]].drop_duplicates()

        # Filter out empty/null values
        hebrew_words = hebrew_words[
            (hebrew_words["he_word"].notna()) &
            (hebrew_words["he_word"] != "") &
            (hebrew_words["he_ipa"].notna()) &
            (hebrew_words["he_ipa"] != "")
        ]

        validation_results = []

        for _, row in hebrew_words.iterrows():
            hebrew = row["he_word"]
            existing_ipa = row["he_ipa"]

            # Generate new IPA
            result = ipa_generator.test_against_existing(hebrew, existing_ipa)
            validation_results.append(result)

        # Calculate accuracy metrics
        exact_matches = sum(1 for r in validation_results if r["exact_match"])
        high_similarity = sum(1 for r in validation_results if r["similarity"] >= 0.7)

        total = len(validation_results)

        if total > 0:
            exact_match_rate = exact_matches / total
            high_similarity_rate = high_similarity / total

            print(f"\nIPA Validation Results:")
            print(f"  Total words tested: {total}")
            print(f"  Exact matches: {exact_matches} ({exact_match_rate:.1%})")
            print(f"  High similarity (≥70%): {high_similarity} ({high_similarity_rate:.1%})")

            # Show some examples of differences
            differences = [r for r in validation_results if not r["exact_match"]][:5]
            if differences:
                print(f"\nExample differences:")
                for diff in differences:
                    print(f"  {diff['hebrew']}:")
                    print(f"    Existing:  {diff['existing_ipa']}")
                    print(f"    Generated: {diff['generated_ipa']}")
                    print(f"    Similarity: {diff['similarity']:.1%}")

            # Require at least 50% similarity (IPA systems can vary)
            # This is a reasonable threshold given different transcription conventions
            assert high_similarity_rate >= 0.50, (
                f"IPA similarity too low: {high_similarity_rate:.1%}. "
                "Expected at least 50% of words with ≥70% similarity."
            )

    def test_consistency_across_regeneration(self, enriched_df, ipa_generator):
        """Test that IPA generation is consistent across multiple runs."""
        # Get a sample of Hebrew words
        sample_words = enriched_df["he_word"].dropna().drop_duplicates().head(10).tolist()

        for word in sample_words:
            if word and word != "":
                # Generate IPA twice
                ipa_1 = ipa_generator.generate_ipa(word)
                ipa_2 = ipa_generator.generate_ipa(word)

                # Should be identical
                assert ipa_1 == ipa_2, f"Inconsistent IPA generation for {word}: {ipa_1} vs {ipa_2}"


class TestDataQualityMetrics:
    """Test data quality metrics for the generated dictionary."""

    @pytest.fixture
    def enriched_df(self):
        """Load enriched entries DataFrame."""
        path = Path("data/03_primary/enriched_entries.parquet")
        if not path.exists():
            pytest.skip("Enriched entries not found. Run pipeline first.")

        return pd.read_parquet(path)

    def test_alignment_coverage(self, enriched_df):
        """Test that alignment produced sufficient coverage."""
        total_entries = len(enriched_df)

        assert total_entries > 0, "No aligned entries found"

        # Check match type distribution
        if "match_type" in enriched_df.columns:
            match_type_counts = enriched_df["match_type"].value_counts()
            print(f"\nMatch type distribution:")
            for match_type, count in match_type_counts.items():
                print(f"  {match_type}: {count} ({count/total_entries:.1%})")

            # Should have some direct matches
            direct_matches = enriched_df[enriched_df["match_type"] == "direct"]
            assert len(direct_matches) > 0, "No direct matches found"

    def test_definition_quality(self, enriched_df):
        """Test that definitions are non-empty and meaningful."""
        # Check Spanish definitions
        empty_es_defs = enriched_df[
            (enriched_df["es_definition"].isna()) |
            (enriched_df["es_definition"] == "")
        ]

        empty_rate_es = len(empty_es_defs) / len(enriched_df)
        assert empty_rate_es < 0.10, f"Too many empty Spanish definitions: {empty_rate_es:.1%}"

        # Check definition lengths (should be meaningful text)
        if "es_definition" in enriched_df.columns:
            avg_def_length = enriched_df["es_definition"].str.len().mean()
            assert avg_def_length > 10, f"Definitions too short on average: {avg_def_length:.1f} chars"

    def test_pos_tag_coverage(self, enriched_df):
        """Test that POS tags are present and valid."""
        if "es_pos" in enriched_df.columns:
            empty_pos = enriched_df[
                (enriched_df["es_pos"].isna()) |
                (enriched_df["es_pos"] == "") |
                (enriched_df["es_pos"] == "unknown")
            ]

            pos_coverage = 1 - (len(empty_pos) / len(enriched_df))
            assert pos_coverage >= 0.90, f"POS tag coverage too low: {pos_coverage:.1%}"

            # Check for common POS tags
            valid_pos_tags = ["noun", "verb", "adj", "adv", "pron", "prep", "conj", "det"]
            pos_counts = enriched_df["es_pos"].value_counts()

            # Should have nouns and verbs at minimum
            assert "noun" in pos_counts.index, "No nouns found"


class TestExampleSentences:
    """Test example sentence quality."""

    @pytest.fixture
    def dictionary_data(self):
        """Load the generated dictionary."""
        path = Path("data/08_reporting/dictionary_v1.json")
        if not path.exists():
            pytest.skip("Dictionary not found. Run pipeline first.")

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def test_examples_have_both_languages(self, dictionary_data):
        """Validate example sentences have both Spanish and Hebrew."""
        entries_with_examples = []
        invalid_examples = []

        for entry in dictionary_data["entries"]:
            for sense in entry["entry"]["senses"]:
                examples = sense.get("examples", [])

                if len(examples) > 0:
                    entries_with_examples.append(entry["entry"]["word"])

                    for example in examples:
                        if "es" not in example or "he" not in example:
                            invalid_examples.append({
                                "word": entry["entry"]["word"],
                                "example": example
                            })

                        # Check both are non-empty
                        if not example.get("es") or not example.get("he"):
                            invalid_examples.append({
                                "word": entry["entry"]["word"],
                                "example": example,
                                "issue": "Empty language field"
                            })

        assert len(invalid_examples) == 0, (
            f"Found {len(invalid_examples)} invalid examples:\n" +
            "\n".join(str(x) for x in invalid_examples[:5])
        )

        # At least some entries should have examples
        # (May be low if Tatoeba sample is small)
        if len(entries_with_examples) > 0:
            print(f"\n{len(entries_with_examples)} entries have example sentences")
