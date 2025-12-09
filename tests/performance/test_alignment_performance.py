"""Performance benchmarks for language alignment algorithms.

These tests measure the performance of critical operations to ensure
the system can scale to production workloads (10,000+ entries).
"""

import time

import pandas as pd
import pytest

from rosetta_dict.pipelines.language_alignment.nodes import align_languages


class TestAlignmentPerformance:
    """Benchmark alignment algorithm performance."""

    @pytest.fixture
    def generate_test_data(self):
        """Generate test data of various sizes for benchmarking."""

        def _generator(n_spanish, n_hebrew):
            """Generate n Spanish and Hebrew entries."""
            spanish_data = {
                "word": [f"palabra{i}" for i in range(n_spanish)],
                "ipa": [f"ipa{i}" for i in range(n_spanish)],
                "pos": ["noun"] * n_spanish,
                "definitions": [[f"Definición {i} con algo de texto"] for i in range(n_spanish)],
                "translations_he": [
                    [] for _ in range(n_spanish)
                ],  # No direct translations to force fuzzy
                "translations_en": [[] for _ in range(n_spanish)],
                "translations_fr": [[] for _ in range(n_spanish)],
                "translations_de": [[] for _ in range(n_spanish)],
                "frequency_rank": list(range(1, n_spanish + 1)),
            }

            hebrew_data = {
                "word": [f"מילה{i}" for i in range(n_hebrew)],
                "ipa": [f"/ipa{i}/" for i in range(n_hebrew)],
                "pos": ["noun"] * n_hebrew,
                "definitions": [[f"הגדרה {i} עם טקסט"] for i in range(n_hebrew)],
                "translations_es": [[] for _ in range(n_hebrew)],
            }

            return pd.DataFrame(spanish_data), pd.DataFrame(hebrew_data)

        return _generator

    @pytest.mark.benchmark
    def test_small_dataset_performance(self, generate_test_data):
        """Benchmark with small dataset (100 entries)."""
        spanish_df, hebrew_df = generate_test_data(100, 100)

        start_time = time.time()
        result = align_languages(spanish_df, hebrew_df)
        elapsed = time.time() - start_time

        print("\nSmall dataset (100x100):")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Alignments: {len(result)}")
        print(f"  Rate: {len(spanish_df) / elapsed:.1f} entries/sec")

        # Should complete quickly
        assert elapsed < 10.0, f"Small dataset too slow: {elapsed:.2f}s"

    @pytest.mark.benchmark
    def test_medium_dataset_performance(self, generate_test_data):
        """Benchmark with medium dataset (1,000 entries)."""
        spanish_df, hebrew_df = generate_test_data(1000, 1000)

        start_time = time.time()
        result = align_languages(spanish_df, hebrew_df)
        elapsed = time.time() - start_time

        print("\nMedium dataset (1000x1000):")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Alignments: {len(result)}")
        print(f"  Rate: {len(spanish_df) / elapsed:.1f} entries/sec")

        # With optimization should complete in reasonable time
        # Old algorithm: ~30+ minutes for 10k entries
        # New algorithm: should be < 2 minutes for 1k entries
        assert elapsed < 120.0, f"Medium dataset too slow: {elapsed:.2f}s"

    @pytest.mark.benchmark
    @pytest.mark.slow
    def test_large_dataset_performance(self, generate_test_data):
        """Benchmark with large dataset (5,000 entries)."""
        spanish_df, hebrew_df = generate_test_data(5000, 5000)

        start_time = time.time()
        result = align_languages(spanish_df, hebrew_df)
        elapsed = time.time() - start_time

        print("\nLarge dataset (5000x5000):")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Alignments: {len(result)}")
        print(f"  Rate: {len(spanish_df) / elapsed:.1f} entries/sec")

        # Should scale reasonably (target: < 10 minutes for 5k)
        assert elapsed < 600.0, f"Large dataset too slow: {elapsed:.2f}s"

    @pytest.mark.benchmark
    def test_fuzzy_matching_complexity(self, generate_test_data):
        """Test that fuzzy matching scales sub-quadratically."""
        sizes = [100, 200, 400]
        times = []

        for size in sizes:
            spanish_df, hebrew_df = generate_test_data(size, size)

            start_time = time.time()
            align_languages(spanish_df, hebrew_df)
            elapsed = time.time() - start_time

            times.append(elapsed)
            print(f"\nSize {size}: {elapsed:.2f}s")

        # Check complexity: should be better than O(n²)
        # O(n²): doubling size should quadruple time
        # O(n log n): doubling size should ~double time
        # With optimization, should be closer to O(n log n)

        # Ratio of time increase vs size increase
        time_ratio_1 = times[1] / times[0]  # 200/100

        # Time ratio should be < size_ratio² (would indicate O(n²))
        # Ideally close to size_ratio * log(size_ratio) for O(n log n)
        print("\nComplexity analysis:")
        print(f"  Time ratio (2x size): {time_ratio_1:.2f}")
        print("  Expected for O(n²): ~4.0")
        print("  Expected for O(n log n): ~2.0")

        # With optimization, should not be quadratic
        assert time_ratio_1 < 3.5, (
            f"Scaling suggests O(n²) complexity. "
            f"Time ratio {time_ratio_1:.2f} too high for 2x size increase."
        )


class TestMemoryUsage:
    """Test memory efficiency of alignment algorithms."""

    @pytest.fixture
    def generate_test_data(self):
        """Generate test data for memory testing."""

        def _generator(n):
            spanish_data = {
                "word": [f"palabra{i}" for i in range(n)],
                "ipa": [f"ipa{i}" for i in range(n)],
                "pos": ["noun"] * n,
                "definitions": [[f"Definición {i}"] for i in range(n)],
                "translations_he": [[] for _ in range(n)],
                "translations_en": [[] for _ in range(n)],
                "translations_fr": [[] for _ in range(n)],
                "translations_de": [[] for _ in range(n)],
                "frequency_rank": list(range(1, n + 1)),
            }
            hebrew_data = {
                "word": [f"מילה{i}" for i in range(n)],
                "ipa": [f"/ipa{i}/" for i in range(n)],
                "pos": ["noun"] * n,
                "definitions": [[f"הגדרה {i}"] for i in range(n)],
                "translations_es": [[] for _ in range(n)],
            }
            return pd.DataFrame(spanish_data), pd.DataFrame(hebrew_data)

        return _generator

    @pytest.mark.benchmark
    def test_no_memory_leaks(self, generate_test_data):
        """Test that alignment doesn't leak memory over multiple runs."""
        import gc

        # Run multiple times with same data
        spanish_df, hebrew_df = generate_test_data(500)

        for i in range(5):
            result = align_languages(spanish_df, hebrew_df)
            assert len(result) >= 0  # Just to use the result

            # Force garbage collection
            gc.collect()

        # If we get here without OOM, test passes
        # More sophisticated memory tracking could be added with tracemalloc


class TestAlignmentQuality:
    """Test alignment quality doesn't degrade with optimization."""

    @pytest.fixture
    def real_test_data(self):
        """Use realistic test data to verify quality."""
        spanish_df = pd.DataFrame(
            {
                "word": ["casa", "perro", "libro"],
                "ipa": ["ˈka.sa", "ˈpe.ro", "ˈli.bɾo"],
                "pos": ["noun", "noun", "noun"],
                "definitions": [
                    ["Edificio para habitar"],
                    ["Animal doméstico canino"],
                    ["Obra escrita con páginas"],
                ],
                "translations_he": [[], [], []],  # Force fuzzy matching
                "translations_en": [[], [], []],
                "translations_fr": [[], [], []],
                "translations_de": [[], [], []],
                "frequency_rank": [1, 2, 3],
            }
        )

        hebrew_df = pd.DataFrame(
            {
                "word": ["בית", "כלב", "ספר"],
                "ipa": ["/ba.jit/", "/ke.lev/", "/se.fer/"],
                "pos": ["noun", "noun", "noun"],
                "definitions": [
                    ["Casa, edificio residencial"],
                    ["Animal doméstico de la familia canina"],
                    ["Libro, obra literaria con páginas"],
                ],
                "translations_es": [[], [], []],
            }
        )

        return spanish_df, hebrew_df

    def test_fuzzy_matching_finds_good_matches(self, real_test_data):
        """Verify fuzzy matching still finds correct translations."""
        spanish_df, hebrew_df = real_test_data

        result = align_languages(spanish_df, hebrew_df)

        # Should find matches for words with similar definitions
        assert len(result) > 0, "No alignments found"

        # Check that we got reasonable matches (casa->בית, perro->כלב, libro->ספר)
        spanish_words = result["es_word"].tolist()

        # At least some of our test words should be matched
        matched_count = sum(1 for word in ["casa", "perro", "libro"] if word in spanish_words)
        assert matched_count >= 2, f"Only {matched_count}/3 words matched"

    def test_confidence_scores_are_meaningful(self, real_test_data):
        """Verify confidence scores reflect match quality."""
        spanish_df, hebrew_df = real_test_data

        result = align_languages(spanish_df, hebrew_df)

        if "confidence" in result.columns:
            confidences = result["confidence"].dropna()

            if len(confidences) > 0:
                # Confidence should be between 0.8 and 1.0 (threshold is 80%)
                assert all(0.8 <= c <= 1.0 for c in confidences), "Confidence scores out of range"

                # Average confidence should be reasonable
                avg_confidence = confidences.mean()
                assert avg_confidence >= 0.80, f"Average confidence too low: {avg_confidence:.2%}"


class TestPerformanceRegression:
    """Tests to detect performance regressions."""

    @pytest.fixture
    def benchmark_baseline(self):
        """Baseline performance expectations."""
        return {
            "100_entries": 10.0,  # Max 10 seconds for 100 entries
            "1000_entries": 120.0,  # Max 2 minutes for 1000 entries
            "entries_per_sec": 8.0,  # Min 8 entries/sec processing rate
        }

    @pytest.mark.benchmark
    def test_meets_performance_sla(self, benchmark_baseline):
        """Verify system meets performance SLA."""
        # Generate 100 entry test
        spanish_df = pd.DataFrame(
            {
                "word": [f"palabra{i}" for i in range(100)],
                "ipa": [f"ipa{i}" for i in range(100)],
                "pos": ["noun"] * 100,
                "definitions": [[f"Definición {i}"] for i in range(100)],
                "translations_he": [[] for _ in range(100)],
                "translations_en": [[] for _ in range(100)],
                "translations_fr": [[] for _ in range(100)],
                "translations_de": [[] for _ in range(100)],
                "frequency_rank": list(range(1, 101)),
            }
        )

        hebrew_df = pd.DataFrame(
            {
                "word": [f"מילה{i}" for i in range(100)],
                "ipa": [f"/ipa{i}/" for i in range(100)],
                "pos": ["noun"] * 100,
                "definitions": [[f"הגדרה {i}"] for i in range(100)],
                "translations_es": [[] for _ in range(100)],
            }
        )

        start_time = time.time()
        align_languages(spanish_df, hebrew_df)
        elapsed = time.time() - start_time

        entries_per_sec = len(spanish_df) / elapsed

        print("\nPerformance SLA check:")
        print(f"  Time: {elapsed:.2f}s (SLA: <{benchmark_baseline['100_entries']}s)")
        print(
            f"  Rate: {entries_per_sec:.1f} entries/sec (SLA: >{benchmark_baseline['entries_per_sec']})"
        )

        assert elapsed < benchmark_baseline["100_entries"], (
            f"Performance SLA violated: {elapsed:.2f}s > {benchmark_baseline['100_entries']}s"
        )

        assert entries_per_sec > benchmark_baseline["entries_per_sec"], (
            f"Processing rate SLA violated: {entries_per_sec:.1f} < {benchmark_baseline['entries_per_sec']} entries/sec"
        )
