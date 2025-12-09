"""Hebrew IPA (International Phonetic Alphabet) Generator.

This module generates IPA pronunciations for Hebrew words using the phonikud library
for Modern Israeli Hebrew. It includes fallback rule-based generation for cases where
phonikud fails or is unavailable.

Supports:
- Modern Israeli Hebrew (primary)
- Sephardic Hebrew (traditional pronunciation)
- Fallback rule-based generation
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import phonikud, but don't fail if it's not available
try:
    from phonikud import phonemize
    PHONIKUD_AVAILABLE = True
    logger.info("phonikud library loaded successfully")
except ImportError:
    PHONIKUD_AVAILABLE = False
    logger.warning("phonikud library not available, will use fallback rules only")


class HebrewIPAGenerator:
    """Generate IPA pronunciations for Hebrew words."""

    # Load comprehensive lookup table from Wiktionary
    COMMON_WORD_IPA = None  # Will be loaded on first use

    # Modern Israeli Hebrew consonant mappings (fallback)
    CONSONANT_MAP_MODERN = {
        'א': 'ʔ',  # alef - glottal stop
        'ב': 'b',  # bet with dagesh
        'בּ': 'b',  # bet with dagesh (explicit)
        'ג': 'ɡ',  # gimel
        'ד': 'd',  # dalet
        'ה': 'h',  # he
        'ו': 'v',  # vav as consonant
        'ז': 'z',  # zayin
        'ח': 'χ',  # chet - uvular fricative (merged with kaf in Modern Hebrew)
        'ט': 't',  # tet
        'י': 'j',  # yod
        'כ': 'k',  # kaf with dagesh
        'כּ': 'k',  # kaf with dagesh (explicit)
        'ך': 'χ',  # final khaf
        'ל': 'l',  # lamed
        'מ': 'm',  # mem
        'ם': 'm',  # final mem
        'נ': 'n',  # nun
        'ן': 'n',  # final nun
        'ס': 's',  # samekh
        'ע': 'ʔ',  # ayin - glottal stop (merged in Modern Hebrew)
        'פ': 'p',  # pe with dagesh
        'פּ': 'p',  # pe with dagesh (explicit)
        'ף': 'f',  # final fe
        'צ': 'ts',  # tsadi
        'ץ': 'ts',  # final tsadi
        'ק': 'k',  # qof
        'ר': 'ʁ',  # resh - uvular approximant (French-like r)
        'ש': 'ʃ',  # shin
        'שׂ': 's',  # sin
        'ת': 't',  # tav
    }

    # Sephardic Hebrew consonant mappings (traditional)
    CONSONANT_MAP_SEPHARDIC = {
        **CONSONANT_MAP_MODERN,
        'ר': 'r',  # resh - alveolar trill (Spanish-like r)
        'ח': 'ħ',  # chet - pharyngeal fricative (preserved)
        'ע': 'ʕ',  # ayin - pharyngeal fricative (preserved)
    }

    # Vowel mappings (niqqud to IPA)
    VOWEL_MAP = {
        'ַ': 'a',   # patach
        'ָ': 'a',   # kamatz
        'ֶ': 'e',   # segol
        'ֵ': 'e',   # tsere
        'ִ': 'i',   # hiriq
        'ֹ': 'o',   # holam
        'ֻ': 'u',   # kubutz
        'וּ': 'u',  # shuruk
        'ְ': 'ə',   # shva (when pronounced)
    }

    def __init__(self, variant: str = "modern", use_phonikud: bool = True,
                 fallback_to_rules: bool = True):
        """Initialize the Hebrew IPA generator.

        Args:
            variant: Hebrew variant - "modern", "sephardic", or "yiddish"
            use_phonikud: Whether to use phonikud library if available
            fallback_to_rules: Whether to use rule-based generation if phonikud fails
        """
        self.variant = variant.lower()
        self.use_phonikud = use_phonikud and PHONIKUD_AVAILABLE
        self.fallback_to_rules = fallback_to_rules

        # Load lookup table on first use
        if HebrewIPAGenerator.COMMON_WORD_IPA is None:
            try:
                from rosetta_dict.pipelines.phonemization.hebrew_ipa_lookup import (
                    COMMON_WORD_IPA as lookup,
                )
                HebrewIPAGenerator.COMMON_WORD_IPA = lookup
                logger.info(f"Loaded {len(lookup)} words from IPA lookup table")
            except ImportError:
                logger.warning("Could not load IPA lookup table, using empty dictionary")
                HebrewIPAGenerator.COMMON_WORD_IPA = {}

        # Select consonant map based on variant
        if self.variant == "sephardic":
            self.consonant_map = self.CONSONANT_MAP_SEPHARDIC
        else:
            self.consonant_map = self.CONSONANT_MAP_MODERN

        logger.info(f"Initialized HebrewIPAGenerator with variant={variant}, "
                   f"phonikud={self.use_phonikud}, fallback={fallback_to_rules}")

    def generate_ipa(self, hebrew_word: str) -> Optional[str]:
        """Generate IPA pronunciation for a Hebrew word.

        Args:
            hebrew_word: Hebrew word (may include niqqud/vowel points)

        Returns:
            IPA pronunciation string, or None if generation fails
        """
        if not hebrew_word or not isinstance(hebrew_word, str):
            return None

        # Remove any existing IPA brackets if present
        hebrew_word = hebrew_word.strip()

        # First, check common word lookup table (for both single and multi-word)
        if hebrew_word in self.COMMON_WORD_IPA:
            ipa = self.COMMON_WORD_IPA[hebrew_word]
            logger.debug(f"lookup: {hebrew_word} → {ipa}")
            return f"/{ipa}/"

        # Handle multi-word phrases by splitting and processing each word
        if ' ' in hebrew_word:
            return self._generate_multiword_ipa(hebrew_word, separator=' ')
        elif '-' in hebrew_word:
            return self._generate_multiword_ipa(hebrew_word, separator='-')

        # Single word processing
        return self._generate_single_word_ipa(hebrew_word)

    def _generate_multiword_ipa(self, phrase: str, separator: str) -> Optional[str]:
        """Generate IPA for multi-word phrases.

        Args:
            phrase: Multi-word Hebrew phrase
            separator: Separator between words (' ' or '-')

        Returns:
            IPA pronunciation string, or None if generation fails
        """
        words = phrase.split(separator)
        ipa_parts = []

        for word in words:
            word = word.strip()
            if not word:
                continue

            # Try to generate IPA for each word
            word_ipa = self._generate_single_word_ipa(word)

            if word_ipa:
                # Remove slashes for combining
                clean_ipa = word_ipa.strip('/')
                ipa_parts.append(clean_ipa)
            else:
                # If any word fails, return None
                logger.debug(f"Failed to generate IPA for word '{word}' in phrase '{phrase}'")
                return None

        if ipa_parts:
            # Combine with original separator
            combined = separator.join(ipa_parts)
            logger.debug(f"multiword: {phrase} → {combined}")
            return f"/{combined}/"

        return None

    def _generate_single_word_ipa(self, hebrew_word: str) -> Optional[str]:
        """Generate IPA for a single Hebrew word.

        Args:
            hebrew_word: Single Hebrew word

        Returns:
            IPA pronunciation string, or None if generation fails
        """
        if not hebrew_word:
            return None

        # Check lookup table first
        if hebrew_word in self.COMMON_WORD_IPA:
            ipa = self.COMMON_WORD_IPA[hebrew_word]
            return f"/{ipa}/"

        # Try phonikud if enabled
        if self.use_phonikud:
            try:
                ipa = self._generate_with_phonikud(hebrew_word)
                if ipa:
                    logger.debug(f"phonikud: {hebrew_word} → {ipa}")
                    return ipa
            except Exception as e:
                logger.debug(f"phonikud failed for '{hebrew_word}': {e}")

        # Fallback to rule-based generation
        if self.fallback_to_rules:
            try:
                ipa = self._generate_with_rules(hebrew_word)
                if ipa:
                    logger.debug(f"rules: {hebrew_word} → {ipa}")
                    return ipa
            except Exception as e:
                logger.warning(f"Rule-based generation failed for '{hebrew_word}': {e}")

        return None

    def _generate_with_phonikud(self, hebrew_word: str) -> Optional[str]:
        """Generate IPA using the phonikud library.
        
        Args:
            hebrew_word: Hebrew word
            
        Returns:
            IPA string or None
        """
        if not PHONIKUD_AVAILABLE:
            return None

        try:
            # phonikud.phonemize returns IPA transcription
            ipa = phonemize(hebrew_word)

            # Clean up the output
            if ipa:
                ipa = ipa.strip()
                # Remove brackets if phonikud adds them
                ipa = ipa.strip('[]/')
                return f"/{ipa}/" if ipa else None

        except Exception as e:
            logger.debug(f"phonikud error for '{hebrew_word}': {e}")
            return None

        return None

    def _generate_with_rules(self, hebrew_word: str) -> Optional[str]:
        """Generate IPA using enhanced rule-based mapping.

        This improved version includes:
        - Comprehensive consonant mapping
        - Vowel inference for unvocalized text
        - Common Hebrew phonological rules
        - Better handling of matres lectionis (ו, י as vowels)

        Args:
            hebrew_word: Hebrew word

        Returns:
            IPA string or None
        """
        if not hebrew_word:
            return None

        ipa_parts = []
        i = 0

        while i < len(hebrew_word):
            char = hebrew_word[i]
            next_char = hebrew_word[i+1] if i + 1 < len(hebrew_word) else None
            prev_char = hebrew_word[i-1] if i > 0 else None

            # Check for two-character combinations first
            if next_char:
                two_char = hebrew_word[i:i+2]
                if two_char in self.consonant_map:
                    ipa_parts.append(self.consonant_map[two_char])
                    i += 2
                    continue

            # Handle niqqud (vowel points) first
            if char in self.VOWEL_MAP:
                ipa_parts.append(self.VOWEL_MAP[char])
                i += 1
                continue

            # Handle consonants with mater lectionis vowel inference
            if char in self.consonant_map:
                # Add the consonant
                consonant_ipa = self.consonant_map[char]
                ipa_parts.append(consonant_ipa)

                # Infer vowels for common patterns (matres lectionis)
                # Only if no niqqud follows
                if next_char and next_char not in self.VOWEL_MAP:
                    # ו as vowel (vav) - usually /o/ or /u/
                    if char == 'ו' and prev_char and prev_char in self.consonant_map:
                        # Replace last consonant (v) with vowel
                        ipa_parts[-1] = 'o'
                    # יי pattern often represents /aj/ or /e/
                    elif char == 'י' and next_char == 'י':
                        ipa_parts.append('j')
                        i += 1  # Skip next י
                    # Single י between consonants often silent or /i/
                    elif char == 'י' and next_char and next_char in self.consonant_map:
                        # י as vowel /i/ between consonants
                        if prev_char and prev_char in self.consonant_map:
                            # Keep as /j/ consonant for now
                            pass

                i += 1
                continue

            # Skip unrecognized characters (punctuation, etc.)
            i += 1

        if ipa_parts:
            ipa = ''.join(ipa_parts)
            return f"/{ipa}/" if ipa else None

        return None

    def test_against_existing(self, hebrew_word: str, existing_ipa: str) -> Dict[str, any]:
        """Test generation against existing IPA to validate accuracy.
        
        Args:
            hebrew_word: Hebrew word
            existing_ipa: Known correct IPA pronunciation
            
        Returns:
            Dictionary with test results
        """
        generated_ipa = self.generate_ipa(hebrew_word)

        # Normalize both for comparison (remove brackets, whitespace)
        def normalize(ipa_str):
            if not ipa_str:
                return ""
            return ipa_str.strip().strip('[]/')

        gen_norm = normalize(generated_ipa)
        exist_norm = normalize(existing_ipa)

        # Calculate simple similarity (exact match or character overlap)
        exact_match = gen_norm == exist_norm

        if gen_norm and exist_norm:
            # Simple character overlap ratio
            common_chars = sum(1 for c in gen_norm if c in exist_norm)
            similarity = common_chars / max(len(gen_norm), len(exist_norm))
        else:
            similarity = 0.0

        return {
            "hebrew": hebrew_word,
            "existing_ipa": existing_ipa,
            "generated_ipa": generated_ipa,
            "exact_match": exact_match,
            "similarity": similarity,
            "method": "phonikud" if self.use_phonikud and PHONIKUD_AVAILABLE else "rules"
        }


def generate_hebrew_ipa_for_entries(entries: List[Dict],
                                     variant: str = "modern",
                                     skip_existing: bool = True) -> List[Dict]:
    """Generate Hebrew IPA for dictionary entries.
    
    Args:
        entries: List of dictionary entry dictionaries
        variant: Hebrew variant ("modern", "sephardic", "yiddish")
        skip_existing: If True, don't overwrite existing IPA values
        
    Returns:
        Updated entries with generated IPA
    """
    generator = HebrewIPAGenerator(variant=variant)

    total_senses = 0
    generated_count = 0
    skipped_count = 0
    failed_count = 0

    for entry_dict in entries:
        entry = entry_dict.get("entry", {})
        senses = entry.get("senses", [])

        for sense in senses:
            total_senses += 1

            # Skip if already has IPA and skip_existing is True
            if skip_existing and sense.get("ipa_hebrew"):
                skipped_count += 1
                continue

            hebrew_word = sense.get("hebrew", "")
            if not hebrew_word:
                failed_count += 1
                continue

            # Generate IPA
            ipa = generator.generate_ipa(hebrew_word)

            if ipa:
                sense["ipa_hebrew"] = ipa
                generated_count += 1
            else:
                failed_count += 1

    logger.info("Hebrew IPA generation complete:")
    logger.info(f"  Total senses: {total_senses}")
    logger.info(f"  Generated: {generated_count}")
    logger.info(f"  Skipped (existing): {skipped_count}")
    logger.info(f"  Failed: {failed_count}")

    return entries
