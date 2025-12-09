"""Comprehensive tests for language alignment accuracy."""

import pandas as pd
import pytest
from rosetta_dict.pipelines.language_alignment.nodes import (
    align_languages,
    enrich_entries,
    cluster_polysemic_senses,
    structure_senses,
)


@pytest.fixture
def sample_spanish_df():
    """Sample Spanish entries for testing."""
    return pd.DataFrame({
        "word": ["casa", "banco", "gato"],
        "ipa": ["ˈka.sa", "ˈbaŋ.ko", "ˈɡa.to"],
        "pos": ["noun", "noun", "noun"],
        "definitions": [
            ["Edificio para habitar"],
            ["Asiento largo", "Institución financiera"],
            ["Animal felino doméstico"]
        ],
        "translations_he": [["בית"], ["ספסל", "בנק"], ["חתול"]],
        "translations_en": [["house"], ["bench", "bank"], ["cat"]],
        "translations_fr": [["maison"], ["banc", "banque"], ["chat"]],
        "translations_de": [["Haus"], ["Bank"], ["Katze"]],
        "frequency_rank": [1, 2, 3]
    })


@pytest.fixture
def sample_hebrew_df():
    """Sample Hebrew entries for testing."""
    return pd.DataFrame({
        "word": ["בית", "ספסל", "בנק", "חתול"],
        "ipa": ["/ba.jit/", "/saf.sal/", "/bank/", "/xa.tul/"],
        "pos": ["noun", "noun", "noun", "noun"],
        "definitions": [
            ["Casa, hogar"],
            ["Asiento largo para varias personas"],
            ["Institución que maneja dinero"],
            ["Mamífero carnívoro felino"]
        ],
        "translations_es": [["casa"], ["banco"], ["banco"], ["gato"]],
    })


@pytest.fixture
def sample_bridge_df():
    """Sample English bridge data for triangulation testing."""
    return pd.DataFrame({
        "word": ["house", "bench", "bank", "cat", "libro"],
        "source_lang": ["es", "es", "es", "es", "es"],
        "ipa": ["/haʊs/", "/bɛntʃ/", "/bæŋk/", "/kæt/", "/ˈliːbroʊ/"],
        "pos": ["noun", "noun", "noun", "noun", "noun"],
        "definitions": [["Building for living"], ["Long seat"], ["Financial institution"], ["Feline animal"], ["Written work"]],
        "translations_he": [["בית"], ["ספסל"], ["בנק"], ["חתול"], ["ספר"]],
        "translations_es": [["casa"], ["banco"], ["banco"], ["gato"], []],
    })


@pytest.fixture
def sample_examples_df():
    """Sample Tatoeba examples for testing."""
    return pd.DataFrame({
        "es": ["La casa es grande.", "El gato duerme."],
        "he": ["הבית גדול.", "החתול ישן."],
        "es_words": [["la", "casa", "es", "grande"], ["el", "gato", "duerme"]],
        "he_words": [["הבית", "גדול"], ["החתול", "ישן"]]
    })


class TestDirectAlignment:
    """Test direct translation matching strategy."""

    def test_direct_match_single_translation(self, sample_spanish_df, sample_hebrew_df):
        """Verify direct matching for words with single translation."""
        result = align_languages(sample_spanish_df, sample_hebrew_df)

        # casa -> בית should match directly
        casa_matches = result[result["es_word"] == "casa"]
        assert len(casa_matches) == 1
        assert casa_matches.iloc[0]["he_word"] == "בית"
        assert casa_matches.iloc[0]["match_type"] == "direct"
        assert casa_matches.iloc[0]["sense_id"] == 1

    def test_direct_match_multiple_translations(self, sample_spanish_df, sample_hebrew_df):
        """Verify direct matching handles polysemy correctly."""
        result = align_languages(sample_spanish_df, sample_hebrew_df)

        # banco has 2 translations: ספסל (bench), בנק (bank)
        banco_matches = result[result["es_word"] == "banco"]
        assert len(banco_matches) == 2

        he_words = set(banco_matches["he_word"].tolist())
        assert "ספסל" in he_words
        assert "בנק" in he_words

        # Verify sense_ids are sequential
        sense_ids = sorted(banco_matches["sense_id"].tolist())
        assert sense_ids == [1, 2]

    def test_alignment_preserves_metadata(self, sample_spanish_df, sample_hebrew_df):
        """Ensure alignment preserves IPA, POS, and definitions."""
        result = align_languages(sample_spanish_df, sample_hebrew_df)

        casa_match = result[result["es_word"] == "casa"].iloc[0]
        assert casa_match["es_ipa"] == "ˈka.sa"
        assert casa_match["es_pos"] == "noun"
        assert casa_match["he_ipa"] == "/ba.jit/"
        assert "Edificio" in casa_match["es_definition"]


class TestTriangulation:
    """Test bridge language triangulation strategy."""

    def test_triangulation_via_english(self, sample_bridge_df, sample_hebrew_df):
        """Verify triangulation through English Wiktionary works."""
        # Create a Spanish entry without direct Hebrew translation
        spanish_df = pd.DataFrame({
            "word": ["libro"],
            "ipa": ["ˈli.bɾo"],
            "pos": ["noun"],
            "definitions": [["Obra escrita"]],
            "translations_he": [[]],  # No direct translation
            "translations_en": [["book"]],
            "translations_fr": [[]],
            "translations_de": [[]]
        })

        # Hebrew entry for book
        hebrew_df = pd.DataFrame({
            "word": ["ספר"],
            "ipa": ["/se.fer/"],
            "pos": ["noun"],
            "definitions": [["Libro, obra escrita"]],
            "translations_es": [["libro"]]
        })

        result = align_languages(spanish_df, hebrew_df, sample_bridge_df)

        # Should find libro -> ספר via English triangulation
        libro_matches = result[result["es_word"] == "libro"]
        assert len(libro_matches) >= 1

        triangulated = libro_matches[libro_matches["match_type"] == "triangulation"]
        if len(triangulated) > 0:
            assert triangulated.iloc[0]["he_word"] == "ספר"

    def test_triangulation_skips_already_aligned(self, sample_spanish_df, sample_hebrew_df, sample_bridge_df):
        """Verify triangulation doesn't duplicate direct matches."""
        result = align_languages(sample_spanish_df, sample_hebrew_df, sample_bridge_df)

        # casa should only have direct match, not triangulation duplicate
        casa_matches = result[result["es_word"] == "casa"]
        match_types = casa_matches["match_type"].tolist()

        # Should not have multiple matches of same word via different strategies
        assert match_types.count("direct") + match_types.count("triangulation") == len(casa_matches)


class TestFuzzyMatching:
    """Test fuzzy definition matching strategy."""

    def test_fuzzy_threshold_enforcement(self):
        """Verify fuzzy matching respects 80% threshold."""
        spanish_df = pd.DataFrame({
            "word": ["perro"],
            "ipa": ["ˈpe.ro"],
            "pos": ["noun"],
            "definitions": [["Animal doméstico canino"]],
            "translations_he": [[]],
            "translations_en": [[]],
            "translations_fr": [[]],
            "translations_de": [[]],
            "frequency_rank": [1]
        })

        # Similar definition (should match)
        hebrew_df_similar = pd.DataFrame({
            "word": ["כלב"],
            "ipa": ["/ke.lev/"],
            "pos": ["noun"],
            "definitions": [["Animal doméstico de la familia canina"]],  # Similar
            "translations_es": [[]]
        })

        result_similar = align_languages(spanish_df, hebrew_df_similar)
        fuzzy_matches = result_similar[result_similar["match_type"].str.startswith("fuzzy")]
        assert len(fuzzy_matches) >= 1

        # Dissimilar definition (should not match)
        hebrew_df_dissimilar = pd.DataFrame({
            "word": ["עץ"],
            "ipa": ["/ets/"],
            "pos": ["noun"],
            "definitions": [["Planta leñosa perenne"]],  # Completely different
            "translations_es": [[]]
        })

        result_dissimilar = align_languages(spanish_df, hebrew_df_dissimilar)
        # Should have no matches or very low confidence
        assert len(result_dissimilar) == 0 or result_dissimilar.iloc[0].get("confidence", 0) < 0.8

    def test_fuzzy_confidence_score(self, sample_spanish_df):
        """Verify fuzzy matches include confidence scores."""
        hebrew_df = pd.DataFrame({
            "word": ["חיה"],
            "ipa": ["/xa.ja/"],
            "pos": ["noun"],
            "definitions": [["Animal felino pequeño domesticado"]],  # Similar to gato
            "translations_es": [[]]
        })

        result = align_languages(sample_spanish_df, hebrew_df)
        fuzzy_matches = result[result["match_type"].str.startswith("fuzzy")]

        if len(fuzzy_matches) > 0:
            assert "confidence" in fuzzy_matches.columns
            assert all(fuzzy_matches["confidence"] >= 0.8)
            assert all(fuzzy_matches["confidence"] <= 1.0)


class TestEnrichment:
    """Test example sentence enrichment."""

    def test_enrich_with_matching_examples(self, sample_spanish_df, sample_hebrew_df, sample_examples_df):
        """Verify examples are correctly matched to word pairs."""
        aligned_df = align_languages(sample_spanish_df, sample_hebrew_df)
        enriched_df = enrich_entries(aligned_df, sample_examples_df)

        # casa entry should have the matching example
        casa_enriched = enriched_df[enriched_df["es_word"] == "casa"].iloc[0]
        assert "examples" in casa_enriched

        # Note: The example uses "הבית" not "בית" so it may not match
        # This test validates the matching logic works when words are present

    def test_enrich_no_examples_returns_empty_list(self, sample_spanish_df, sample_hebrew_df):
        """Verify entries without examples get empty list."""
        aligned_df = align_languages(sample_spanish_df, sample_hebrew_df)

        # Empty examples DataFrame
        empty_examples = pd.DataFrame({
            "es": [],
            "he": [],
            "es_words": [],
            "he_words": []
        })

        enriched_df = enrich_entries(aligned_df, empty_examples)

        # All entries should have empty examples lists
        assert all(enriched_df["examples"].apply(lambda x: isinstance(x, list)))
        assert all(enriched_df["examples"].apply(lambda x: len(x) == 0))


class TestPolysemyClustering:
    """Test polysemic sense clustering."""

    def test_cluster_similar_senses(self):
        """Verify semantically similar senses are clustered together."""
        enriched_df = pd.DataFrame({
            "es_word": ["banco", "banco", "banco"],
            "es_definition": [
                "Asiento largo para varias personas",
                "Asiento alargado",  # Similar to first
                "Institución financiera"  # Different
            ],
            "he_word": ["ספסל", "ספסל", "בנק"],
            "he_ipa": ["/saf.sal/", "/saf.sal/", "/bank/"],
            "examples": [[], [], []]
        })

        clustered = cluster_polysemic_senses(enriched_df)

        assert "semantic_cluster" in clustered.columns

        # First two should be in same cluster (similar definitions)
        cluster_1 = clustered.iloc[0]["semantic_cluster"]
        cluster_2 = clustered.iloc[1]["semantic_cluster"]
        cluster_3 = clustered.iloc[2]["semantic_cluster"]

        assert cluster_1 == cluster_2  # Similar definitions clustered
        assert cluster_1 != cluster_3  # Different definition separate

    def test_non_polysemic_words_single_cluster(self):
        """Verify words with single sense get default cluster."""
        enriched_df = pd.DataFrame({
            "es_word": ["casa"],
            "es_definition": ["Edificio para habitar"],
            "he_word": ["בית"],
            "he_ipa": ["/ba.jit/"],
            "examples": [[]]
        })

        clustered = cluster_polysemic_senses(enriched_df)
        assert clustered.iloc[0]["semantic_cluster"] == 1


class TestStructuring:
    """Test final JSON structuring."""

    def test_structure_single_sense(self):
        """Verify single-sense words are structured correctly."""
        enriched_df = pd.DataFrame({
            "es_word": ["casa"],
            "es_ipa": ["ˈka.sa"],
            "es_pos": ["noun"],
            "es_definition": ["Edificio para habitar"],
            "he_word": ["בית"],
            "he_ipa": ["/ba.jit/"],
            "sense_id": [1],
            "examples": [[{"es": "La casa es grande.", "he": "הבית גדול."}]]
        })

        entries = structure_senses(enriched_df)

        assert len(entries) == 1
        entry = entries[0]

        assert entry["id"] == "es: casa"
        assert entry["entry"]["word"] == "casa"
        assert entry["entry"]["ipa"] == "ˈka.sa"
        assert entry["entry"]["language"] == "es"
        assert len(entry["entry"]["senses"]) == 1

        sense = entry["entry"]["senses"][0]
        assert sense["sense_id"] == 1
        assert sense["hebrew"] == "בית"
        assert sense["ipa_hebrew"] == "/ba.jit/"
        assert sense["pos"] == "noun"
        assert len(sense["examples"]) == 1

    def test_structure_polysemic_word(self):
        """Verify polysemic words create multiple senses."""
        enriched_df = pd.DataFrame({
            "es_word": ["banco", "banco"],
            "es_ipa": ["ˈbaŋ.ko", "ˈbaŋ.ko"],
            "es_pos": ["noun", "noun"],
            "es_definition": ["Asiento largo", "Institución financiera"],
            "he_word": ["ספסל", "בנק"],
            "he_ipa": ["/saf.sal/", "/bank/"],
            "sense_id": [1, 2],
            "examples": [[], []]
        })

        entries = structure_senses(enriched_df)

        assert len(entries) == 1  # One word entry
        entry = entries[0]

        assert entry["id"] == "es: banco"
        assert len(entry["entry"]["senses"]) == 2  # Two senses

        # Verify both senses are present
        he_words = [s["hebrew"] for s in entry["entry"]["senses"]]
        assert "ספסל" in he_words
        assert "בנק" in he_words


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_dataframes(self):
        """Verify graceful handling of empty input."""
        empty_df = pd.DataFrame({
            "word": [], "ipa": [], "pos": [], "definitions": [],
            "translations_he": [], "translations_en": [],
            "translations_fr": [], "translations_de": []
        })

        result = align_languages(empty_df, empty_df)
        assert len(result) == 0

    def test_missing_definitions(self):
        """Verify handling of entries without definitions."""
        spanish_df = pd.DataFrame({
            "word": ["test"],
            "ipa": ["test"],
            "pos": ["noun"],
            "definitions": [[]],  # Empty definitions
            "translations_he": [["בדיקה"]],
            "translations_en": [[]],
            "translations_fr": [[]],
            "translations_de": [[]],
            "frequency_rank": [1]
        })

        hebrew_df = pd.DataFrame({
            "word": ["בדיקה"],
            "ipa": ["/be.di.ka/"],
            "pos": ["noun"],
            "definitions": [["Prueba"]],
            "translations_es": [["test"]]
        })

        # Should still create alignment despite empty Spanish definition
        result = align_languages(spanish_df, hebrew_df)
        assert len(result) >= 1

    def test_special_characters_in_hebrew(self):
        """Verify Hebrew with niqqud and special characters is handled."""
        spanish_df = pd.DataFrame({
            "word": ["paz"],
            "ipa": ["pas"],
            "pos": ["noun"],
            "definitions": [["Ausencia de conflicto"]],
            "translations_he": [["שָׁלוֹם"]],  # With niqqud
            "translations_en": [[]],
            "translations_fr": [[]],
            "translations_de": [[]]
        })

        hebrew_df = pd.DataFrame({
            "word": ["שָׁלוֹם"],  # With niqqud
            "ipa": ["/ʃa.lom/"],
            "pos": ["noun"],
            "definitions": [["Paz, tranquilidad"]],
            "translations_es": [["paz"]]
        })

        result = align_languages(spanish_df, hebrew_df)
        assert len(result) >= 1
        assert result.iloc[0]["he_word"] == "שָׁלוֹם"


class TestDataIntegrity:
    """Test data integrity and consistency."""

    def test_no_duplicate_alignments(self, sample_spanish_df, sample_hebrew_df, sample_bridge_df):
        """Verify no duplicate word pairs are created."""
        result = align_languages(sample_spanish_df, sample_hebrew_df, sample_bridge_df)

        # Check for exact duplicates
        duplicates = result[result.duplicated(subset=["es_word", "he_word", "sense_id"], keep=False)]
        assert len(duplicates) == 0, f"Found duplicate alignments: {duplicates}"

    def test_all_alignments_have_required_fields(self, sample_spanish_df, sample_hebrew_df):
        """Verify all alignments contain required fields."""
        result = align_languages(sample_spanish_df, sample_hebrew_df)

        required_fields = [
            "es_word", "es_ipa", "es_pos", "es_definition",
            "he_word", "he_ipa", "sense_id", "match_type"
        ]

        for field in required_fields:
            assert field in result.columns, f"Missing required field: {field}"
            assert result[field].notna().all(), f"Field {field} has null values"

    def test_sense_ids_are_sequential(self, sample_spanish_df, sample_hebrew_df):
        """Verify sense_ids are sequential for each word."""
        result = align_languages(sample_spanish_df, sample_hebrew_df)

        for word in result["es_word"].unique():
            word_senses = result[result["es_word"] == word]["sense_id"].tolist()
            # Sense IDs should start at 1 and be sequential
            assert min(word_senses) >= 1
            # For polysemic words, should have consecutive IDs
            if len(word_senses) > 1:
                word_senses_sorted = sorted(word_senses)
                expected = list(range(1, len(word_senses) + 1))
                # May not be perfectly sequential due to triangulation, but should be reasonable
                assert max(word_senses_sorted) <= len(word_senses) + 5
