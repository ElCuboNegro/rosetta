"""
Book pair validation utilities.

Validates that a Spanish-Hebrew book pair are actually translations of each other
using multiple heuristics and signals.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer, util

logger = logging.getLogger(__name__)


class BookPairValidator:
    """Validates that two books are translations of each other."""

    def __init__(self, model: SentenceTransformer = None):
        """Initialize validator with embedding model."""
        self.model = model
        if self.model is None:
            logger.info("Loading validation model: LaBSE")
            self.model = SentenceTransformer("sentence-transformers/LaBSE")

    def validate_pair(
        self,
        spanish_sentences: List[str],
        hebrew_sentences: List[str],
        spanish_title: str = "",
        hebrew_title: str = "",
        spanish_file: str = "",
        hebrew_file: str = "",
    ) -> Dict:
        """
        Validate that a book pair are translations using multiple signals.

        Returns:
            Dict with validation results:
            {
                'is_valid': bool,
                'confidence': float (0-1),
                'signals': {
                    'sentence_ratio': float,
                    'title_similarity': float,
                    'content_alignment': float,
                    'proper_noun_overlap': float,
                    'numeric_overlap': float,
                    'chapter_structure': float
                },
                'warnings': List[str],
                'recommendation': str ('approve', 'review', 'reject')
            }
        """
        signals = {}
        warnings = []

        # Signal 1: Sentence count ratio
        ratio_signal, ratio_warning = self._check_sentence_ratio(
            len(spanish_sentences), len(hebrew_sentences)
        )
        signals["sentence_ratio"] = ratio_signal
        if ratio_warning:
            warnings.append(ratio_warning)

        # Signal 2: Title similarity
        if spanish_title and hebrew_title:
            title_sim = self._check_title_similarity(spanish_title, hebrew_title)
            signals["title_similarity"] = title_sim
            if title_sim < 0.6:
                warnings.append(f"Low title similarity: {title_sim:.2f}")
        else:
            signals["title_similarity"] = None

        # Signal 3: Content alignment (sample-based)
        content_score, alignment_warning = self._check_content_alignment(
            spanish_sentences, hebrew_sentences
        )
        signals["content_alignment"] = content_score
        if alignment_warning:
            warnings.append(alignment_warning)

        # Signal 4: Proper noun overlap
        noun_overlap = self._check_proper_noun_overlap(
            spanish_sentences[:100],
            hebrew_sentences[:100],  # Sample first 100
        )
        signals["proper_noun_overlap"] = noun_overlap
        if noun_overlap < 0.2:
            warnings.append(
                f"Low proper noun overlap: {noun_overlap:.2f} (expect character/place names to appear in both)"
            )

        # Signal 5: Numeric overlap (years, counts, chapter numbers)
        num_overlap = self._check_numeric_overlap(spanish_sentences[:100], hebrew_sentences[:100])
        signals["numeric_overlap"] = num_overlap
        if num_overlap < 0.3:
            warnings.append(
                f"Low numeric overlap: {num_overlap:.2f} (expect dates/numbers to match)"
            )

        # Signal 6: Chapter structure similarity
        chapter_sim = self._check_chapter_structure(spanish_sentences, hebrew_sentences)
        signals["chapter_structure"] = chapter_sim

        # Compute overall confidence
        confidence, is_valid, recommendation = self._compute_confidence(signals)

        return {
            "is_valid": is_valid,
            "confidence": confidence,
            "signals": signals,
            "warnings": warnings,
            "recommendation": recommendation,
            "details": {
                "spanish_file": spanish_file,
                "hebrew_file": hebrew_file,
                "spanish_sentences": len(spanish_sentences),
                "hebrew_sentences": len(hebrew_sentences),
            },
        }

    def _check_sentence_ratio(self, spanish_count: int, hebrew_count: int) -> Tuple[float, str]:
        """
        Check sentence count ratio.

        Returns:
            (score, warning)
            score: 1.0 if perfect, 0.0 if terrible
        """
        if spanish_count == 0 or hebrew_count == 0:
            return 0.0, "One or both books have no sentences"

        ratio = max(spanish_count, hebrew_count) / min(spanish_count, hebrew_count)

        # Score based on ratio
        if ratio < 1.3:
            score = 1.0  # Perfect
            warning = None
        elif ratio < 2.0:
            score = 0.8  # Good
            warning = None
        elif ratio < 3.0:
            score = 0.4  # Suspicious
            warning = f"Suspicious sentence ratio: {ratio:.1f}:1 (ES: {spanish_count}, HE: {hebrew_count})"
        else:
            score = 0.0  # Terrible
            warning = f"CRITICAL: Sentence ratio {ratio:.1f}:1 suggests different books (ES: {spanish_count}, HE: {hebrew_count})"

        return score, warning

    def _check_title_similarity(self, spanish_title: str, hebrew_title: str) -> float:
        """Check cross-lingual title similarity using embeddings."""
        try:
            titles = [spanish_title, hebrew_title]
            embeddings = self.model.encode(titles, convert_to_tensor=True)
            similarity = util.cos_sim(embeddings[0], embeddings[1]).item()
            return similarity
        except Exception as e:
            logger.warning(f"Title similarity check failed: {e}")
            return 0.0

    def _check_content_alignment(
        self, spanish_sentences: List[str], hebrew_sentences: List[str]
    ) -> Tuple[float, str]:
        """
        Check content alignment quality by sampling sentences.

        Strategy:
        1. Sample sentences from beginning, middle, end
        2. Find best alignment for each
        3. Compute average similarity
        4. High similarity = likely translations
        """
        if len(spanish_sentences) < 10 or len(hebrew_sentences) < 10:
            return 0.0, "Too few sentences to validate alignment"

        try:
            # Sample 45 sentences: 15 from start, 15 from middle, 15 from end
            es_sample = []
            he_sample = []

            # Beginning (avoiding very first lines which might be metadata)
            es_sample.extend(spanish_sentences[10:25])
            he_sample.extend(hebrew_sentences[10:25])

            # Middle
            mid_es = len(spanish_sentences) // 2
            mid_he = len(hebrew_sentences) // 2
            es_sample.extend(spanish_sentences[mid_es - 7 : mid_es + 8])
            he_sample.extend(hebrew_sentences[mid_he - 7 : mid_he + 8])

            # End (avoiding very last lines)
            es_sample.extend(spanish_sentences[-30:-15])
            he_sample.extend(hebrew_sentences[-30:-15])

            # Encode
            es_embeddings = self.model.encode(es_sample, convert_to_tensor=True)
            he_embeddings = self.model.encode(he_sample, convert_to_tensor=True)

            # Find best alignment for each Spanish sentence
            similarities = util.cos_sim(es_embeddings, he_embeddings)
            best_matches = similarities.max(dim=1).values
            avg_similarity = best_matches.mean().item()

            # Interpret score
            if avg_similarity > 0.80:
                warning = None  # Excellent alignment
            elif avg_similarity > 0.70:
                warning = None  # Good alignment
            elif avg_similarity > 0.60:
                warning = f"Moderate content alignment: {avg_similarity:.2f} (may be related but not direct translations)"
            else:
                warning = f"CRITICAL: Low content alignment: {avg_similarity:.2f} (books likely unrelated)"

            return avg_similarity, warning

        except Exception as e:
            logger.warning(f"Content alignment check failed: {e}")
            return 0.0, "Content alignment check failed"

    def _check_proper_noun_overlap(
        self, spanish_sentences: List[str], hebrew_sentences: List[str]
    ) -> float:
        """
        Check if proper nouns (character names, places) appear in both texts.

        Strategy:
        - Extract capitalized words from Spanish (likely proper nouns)
        - Check if they appear in Hebrew (transliterated or translated)
        - Higher overlap = more likely to be same book
        """
        try:
            # Extract capitalized words from Spanish (exclude sentence-initial)
            spanish_text = " ".join(spanish_sentences)
            # Match words that are capitalized and not at sentence start
            spanish_nouns = set(re.findall(r"[.!?]\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)", spanish_text))

            # Also get mid-sentence capitalized words
            spanish_nouns.update(re.findall(r"\s([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,})", spanish_text))

            if not spanish_nouns:
                return 0.5  # Neutral score if no proper nouns found

            # Check Hebrew for transliterations
            # Common Spanish->Hebrew letter mappings
            transliteration_map = {
                "a": ["א", "ע"],
                "e": ["א", "ע", "י"],
                "i": ["י"],
                "o": ["ו", "ע"],
                "u": ["ו"],
                "b": ["ב"],
                "c": ["ק", "כ", "ס"],
                "d": ["ד"],
                "f": ["פ"],
                "g": ["ג"],
                "h": ["ה", "ח"],
                "j": ["ח", "ג"],
                "k": ["ק", "כ"],
                "l": ["ל"],
                "m": ["מ"],
                "n": ["נ"],
                "p": ["פ"],
                "r": ["ר"],
                "s": ["ס"],
                "t": ["ט", "ת"],
                "v": ["ב", "ו"],
                "y": ["י"],
                "z": ["ז"],
            }

            hebrew_text = " ".join(hebrew_sentences).lower()

            # Count how many Spanish proper nouns might appear in Hebrew
            matches = 0
            for noun in spanish_nouns:
                noun_lower = noun.lower()
                if len(noun_lower) >= 3:
                    # FIX: Search for the Hebrew equivalents of the Latin characters
                    # Check first 3 letters - if at least 2 have their Hebrew equivalents present,
                    # we consider it a possible match for this heuristic.
                    char_found_count = 0
                    for char in noun_lower[:4]:
                        hb_chars = transliteration_map.get(char, [])
                        if any(hb_c in hebrew_text for hb_c in hb_chars):
                            char_found_count += 1

                    if char_found_count >= 2:
                        matches += 1

            overlap_score = min(matches / len(spanish_nouns), 1.0) if spanish_nouns else 0.5

            return overlap_score

        except Exception as e:
            logger.warning(f"Proper noun overlap check failed: {e}")
            return 0.5  # Neutral score on error

    def _check_numeric_overlap(
        self, spanish_sentences: List[str], hebrew_sentences: List[str]
    ) -> float:
        """
        Check if numbers (years, counts, chapter numbers) appear in both texts.

        Translations should have the same numbers (years, ages, quantities).
        """
        try:
            # Extract numbers from both texts
            spanish_text = " ".join(spanish_sentences)
            hebrew_text = " ".join(hebrew_sentences)

            # Extract 3-4 digit numbers (likely years, chapter numbers, ages)
            spanish_numbers = set(re.findall(r"\b\d{3,4}\b", spanish_text))
            hebrew_numbers = set(re.findall(r"\b\d{3,4}\b", hebrew_text))

            if not spanish_numbers and not hebrew_numbers:
                return 0.5  # Neutral if no numbers

            if not spanish_numbers or not hebrew_numbers:
                return 0.3  # Low score if only one has numbers

            # Calculate Jaccard similarity
            intersection = spanish_numbers & hebrew_numbers
            union = spanish_numbers | hebrew_numbers

            jaccard = len(intersection) / len(union) if union else 0.0

            return jaccard

        except Exception as e:
            logger.warning(f"Numeric overlap check failed: {e}")
            return 0.5

    def _check_chapter_structure(
        self, spanish_sentences: List[str], hebrew_sentences: List[str]
    ) -> float:
        """
        Check if books have similar chapter/section structure.

        Look for:
        - Chapter markers (CAPÍTULO, פרק)
        - Section breaks (patterns of short sentences)
        - Dialog vs narrative ratios
        """
        try:
            # Count chapter markers
            spanish_chapters = sum(
                1
                for s in spanish_sentences
                if re.search(r"\b(CAPÍTULO|Capítulo|CAPITULO|PARTE|Parte)\b", s)
            )

            hebrew_chapters = sum(1 for s in hebrew_sentences if "פרק" in s or "חלק" in s)

            # If both have chapters and counts are similar
            if spanish_chapters > 0 and hebrew_chapters > 0:
                ratio = max(spanish_chapters, hebrew_chapters) / min(
                    spanish_chapters, hebrew_chapters
                )
                if ratio < 1.5:
                    return 0.9  # Similar chapter structure
                else:
                    return 0.5  # Different chapter counts

            # Check dialog ratio (sentences with quotes)
            spanish_dialog = sum(1 for s in spanish_sentences if '"' in s or "«" in s or "—" in s)
            hebrew_dialog = sum(1 for s in hebrew_sentences if '"' in s or "״" in s or "–" in s)

            spanish_dialog_ratio = (
                spanish_dialog / len(spanish_sentences) if spanish_sentences else 0
            )
            hebrew_dialog_ratio = hebrew_dialog / len(hebrew_sentences) if hebrew_sentences else 0

            # If dialog ratios are similar, books likely have similar structure
            ratio_diff = abs(spanish_dialog_ratio - hebrew_dialog_ratio)

            if ratio_diff < 0.1:
                return 0.8
            elif ratio_diff < 0.2:
                return 0.6
            else:
                return 0.4

        except Exception as e:
            logger.warning(f"Chapter structure check failed: {e}")
            return 0.5

    def _compute_confidence(self, signals: Dict) -> Tuple[float, bool, str]:
        """
        Compute overall confidence and recommendation.

        Returns:
            (confidence, is_valid, recommendation)
        """
        # Weight each signal
        weights = {
            "sentence_ratio": 0.25,  # Very important
            "title_similarity": 0.15,  # Helpful but not decisive
            "content_alignment": 0.35,  # Most important!
            "proper_noun_overlap": 0.10,
            "numeric_overlap": 0.10,
            "chapter_structure": 0.05,
        }

        # Compute weighted average (skip None values)
        total_weight = 0.0
        weighted_sum = 0.0

        for key, weight in weights.items():
            if signals.get(key) is not None:
                weighted_sum += signals[key] * weight
                total_weight += weight

        confidence = weighted_sum / total_weight if total_weight > 0 else 0.0

        # Make recommendation
        if confidence >= 0.75:
            is_valid = True
            recommendation = "approve"
        elif confidence >= 0.55:
            is_valid = True
            recommendation = "review"  # Manual review recommended
        else:
            is_valid = False
            recommendation = "reject"

        return confidence, is_valid, recommendation


def validate_catalog_pairs(
    catalog_df: pd.DataFrame, spanish_dir: Path, hebrew_dir: Path, sample_size: int = 200
) -> pd.DataFrame:
    """
    Validate all pairs in a catalog DataFrame.

    Args:
        catalog_df: DataFrame with gutenberg_id, benyehuda_id, titles
        spanish_dir: Directory containing Spanish books
        hebrew_dir: Directory containing Hebrew books
        sample_size: Number of sentences to sample for validation

    Returns:
        DataFrame with validation results added
    """
    validator = BookPairValidator()

    results = []

    for _, row in catalog_df.iterrows():
        # Load book files
        spanish_file = None
        hebrew_file = None

        # Find Spanish file
        gid = row.get("gutenberg_id")
        if gid:
            spanish_files = list(spanish_dir.glob(f"{gid}_*.txt"))
            if spanish_files:
                spanish_file = spanish_files[0]

        # Find Hebrew file
        byid = row.get("benyehuda_id")
        if byid:
            hebrew_files = list(hebrew_dir.glob(f"**/m{byid}.txt"))
            if hebrew_files:
                hebrew_file = hebrew_files[0]

        if not spanish_file or not hebrew_file:
            continue

        # Read and segment sentences
        try:
            spanish_text = spanish_file.read_text(encoding="utf-8", errors="replace")
            hebrew_text = hebrew_file.read_text(encoding="utf-8", errors="replace")

            # Simple sentence segmentation
            spanish_sents = [s.strip() for s in spanish_text.split(".") if len(s.strip()) > 20]
            hebrew_sents = [s.strip() for s in hebrew_text.split(".") if len(s.strip()) > 10]

            # Sample for efficiency
            spanish_sents = spanish_sents[:sample_size]
            hebrew_sents = hebrew_sents[:sample_size]

            # Validate
            validation = validator.validate_pair(
                spanish_sentences=spanish_sents,
                hebrew_sentences=hebrew_sents,
                spanish_title=row.get("match_title", ""),
                hebrew_title=row.get("he_title", ""),
                spanish_file=str(spanish_file),
                hebrew_file=str(hebrew_file),
            )

            results.append({**row.to_dict(), **validation})

        except Exception as e:
            logger.error(f"Failed to validate {spanish_file} <-> {hebrew_file}: {e}")
            continue

    return pd.DataFrame(results)
