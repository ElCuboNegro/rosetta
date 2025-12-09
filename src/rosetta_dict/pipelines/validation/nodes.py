"""Data validation nodes for quality assurance.

These nodes implement comprehensive schema validation and data quality checks
to prevent silent data degradation in production.
"""

import logging
import pandas as pd
from typing import Dict, List, Any, Tuple
import re

logger = logging.getLogger(__name__)


class DataQualityError(Exception):
    """Raised when data quality checks fail."""
    pass


def validate_wiktionary_entries(df: pd.DataFrame, lang_code: str) -> pd.DataFrame:
    """Validate parsed Wiktionary entries against expected schema.

    Args:
        df: DataFrame with parsed Wiktionary entries
        lang_code: Language code (es, he, en, fr, de)

    Returns:
        Validated DataFrame

    Raises:
        DataQualityError: If validation fails
    """
    logger.info(f"Validating {lang_code} Wiktionary entries ({len(df)} rows)...")

    issues = []

    # Required columns
    required_columns = ["word", "ipa", "pos", "definitions"]
    missing_cols = [col for col in required_columns if col not in df.columns]

    if missing_cols:
        raise DataQualityError(f"Missing required columns: {missing_cols}")

    # Check for empty words
    empty_words = df[df["word"].isna() | (df["word"] == "")]
    if len(empty_words) > 0:
        issues.append(f"Found {len(empty_words)} entries with empty 'word' field")

    # Check for missing POS tags
    missing_pos = df[df["pos"].isna() | (df["pos"] == "") | (df["pos"] == "unknown")]
    if len(missing_pos) > len(df) * 0.2:  # More than 20%
        issues.append(
            f"High rate of missing POS tags: {len(missing_pos)}/{len(df)} "
            f"({len(missing_pos)/len(df)*100:.1f}%)"
        )

    # Check for empty definitions
    empty_defs = df[df["definitions"].apply(lambda x: not x or len(x) == 0)]
    if len(empty_defs) > len(df) * 0.1:  # More than 10%
        issues.append(
            f"High rate of empty definitions: {len(empty_defs)}/{len(df)} "
            f"({len(empty_defs)/len(df)*100:.1f}%)"
        )

    # Language-specific validation
    if lang_code == "he":
        # Validate Hebrew Unicode
        hebrew_pattern = re.compile(r'[\u0590-\u05FF\uFB1D-\uFB4F]+')
        non_hebrew = df[~df["word"].str.contains(hebrew_pattern, na=False)]

        if len(non_hebrew) > len(df) * 0.05:  # More than 5%
            issues.append(
                f"High rate of non-Hebrew words in Hebrew dataset: {len(non_hebrew)}/{len(df)}"
            )

    # Log issues
    if issues:
        logger.warning(f"Data quality issues found in {lang_code} entries:")
        for issue in issues:
            logger.warning(f"  - {issue}")

        # Fail if critical issues
        if len(empty_words) > 0:
            raise DataQualityError(f"Critical: {len(empty_words)} entries with empty words")

    logger.info(f"✓ Validation passed for {lang_code} entries")
    return df


def validate_aligned_matches(df: pd.DataFrame) -> pd.DataFrame:
    """Validate aligned Spanish-Hebrew matches.

    Args:
        df: DataFrame with aligned matches

    Returns:
        Validated DataFrame

    Raises:
        DataQualityError: If validation fails
    """
    logger.info(f"Validating aligned matches ({len(df)} rows)...")

    issues = []

    # Required fields
    required_fields = [
        "es_word", "es_ipa", "es_pos", "es_definition",
        "he_word", "he_ipa", "sense_id", "match_type"
    ]

    missing_fields = [f for f in required_fields if f not in df.columns]
    if missing_fields:
        raise DataQualityError(f"Missing required fields: {missing_fields}")

    # Check for null values in critical fields
    for field in ["es_word", "he_word", "match_type"]:
        null_count = df[field].isna().sum()
        if null_count > 0:
            issues.append(f"Found {null_count} null values in critical field '{field}'")

    # Validate sense_ids
    invalid_sense_ids = df[df["sense_id"] < 1]
    if len(invalid_sense_ids) > 0:
        issues.append(f"Found {len(invalid_sense_ids)} invalid sense_ids (< 1)")

    # Check for duplicate alignments
    duplicates = df.duplicated(subset=["es_word", "he_word", "sense_id"], keep=False)
    dup_count = duplicates.sum()
    if dup_count > 0:
        issues.append(f"Found {dup_count} duplicate alignments")
        logger.warning("Sample duplicates:")
        logger.warning(df[duplicates].head(5)[["es_word", "he_word", "sense_id", "match_type"]])

    # Validate match types
    valid_match_types = ["direct", "triangulation"]
    # Also allow fuzzy_XX where XX is a number
    valid_fuzzy_pattern = re.compile(r'^fuzzy_\d+$')

    invalid_matches = df[
        ~(df["match_type"].isin(valid_match_types) |
          df["match_type"].str.match(valid_fuzzy_pattern, na=False))
    ]

    if len(invalid_matches) > 0:
        issues.append(f"Found {len(invalid_matches)} invalid match_type values")

    # Validate confidence scores for fuzzy matches
    if "confidence" in df.columns:
        fuzzy_matches = df[df["match_type"].str.startswith("fuzzy", na=False)]
        if len(fuzzy_matches) > 0:
            invalid_confidence = fuzzy_matches[
                (fuzzy_matches["confidence"] < 0.0) |
                (fuzzy_matches["confidence"] > 1.0)
            ]

            if len(invalid_confidence) > 0:
                issues.append(f"Found {len(invalid_confidence)} invalid confidence scores")

    # Hebrew Unicode validation
    hebrew_pattern = re.compile(r'[\u0590-\u05FF\uFB1D-\uFB4F]+')
    non_hebrew = df[~df["he_word"].str.contains(hebrew_pattern, na=False)]

    if len(non_hebrew) > 0:
        issues.append(f"Found {len(non_hebrew)} entries without Hebrew characters in he_word")

    # Check IPA coverage
    missing_es_ipa = df[(df["es_ipa"].isna()) | (df["es_ipa"] == "")].count()
    missing_he_ipa = df[(df["he_ipa"].isna()) | (df["he_ipa"] == "")].count()

    ipa_threshold = len(df) * 0.2  # 20% threshold

    if missing_es_ipa > ipa_threshold:
        issues.append(f"Low Spanish IPA coverage: {len(df) - missing_es_ipa}/{len(df)}")

    if missing_he_ipa > ipa_threshold:
        issues.append(f"Low Hebrew IPA coverage: {len(df) - missing_he_ipa}/{len(df)}")

    # Log all issues
    if issues:
        logger.warning(f"Data quality issues in aligned matches:")
        for issue in issues:
            logger.warning(f"  - {issue}")

        # Fail on critical issues
        critical_issues = [i for i in issues if "null values in critical field" in i]
        if critical_issues:
            raise DataQualityError(f"Critical issues found: {critical_issues}")

    logger.info(f"✓ Validation passed for aligned matches")
    return df


def validate_enriched_entries(df: pd.DataFrame) -> pd.DataFrame:
    """Validate enriched entries with examples.

    Args:
        df: DataFrame with enriched entries

    Returns:
        Validated DataFrame

    Raises:
        DataQualityError: If validation fails
    """
    logger.info(f"Validating enriched entries ({len(df)} rows)...")

    # Run aligned matches validation first
    df = validate_aligned_matches(df)

    # Additional validation for examples
    if "examples" in df.columns:
        # Check example structure
        invalid_examples = []

        for idx, row in df.iterrows():
            examples = row["examples"]

            if not isinstance(examples, list):
                invalid_examples.append(f"Row {idx}: examples is not a list")
                continue

            for ex in examples:
                if not isinstance(ex, dict):
                    invalid_examples.append(f"Row {idx}: example is not a dict")
                    continue

                if "es" not in ex or "he" not in ex:
                    invalid_examples.append(f"Row {idx}: missing 'es' or 'he' in example")

        if invalid_examples:
            logger.warning(f"Found {len(invalid_examples)} invalid examples")
            for ex in invalid_examples[:10]:  # Show first 10
                logger.warning(f"  - {ex}")

    logger.info(f"✓ Validation passed for enriched entries")
    return df


def validate_final_dictionary(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate final dictionary JSON structure.

    Args:
        entries: List of dictionary entries

    Returns:
        Validated entries

    Raises:
        DataQualityError: If validation fails
    """
    logger.info(f"Validating final dictionary structure ({len(entries)} entries)...")

    issues = []

    for idx, entry in enumerate(entries):
        # Check top-level structure
        if "id" not in entry:
            issues.append(f"Entry {idx}: missing 'id'")

        if "entry" not in entry:
            issues.append(f"Entry {idx}: missing 'entry'")
            continue

        entry_data = entry["entry"]

        # Check required fields
        required_fields = ["word", "ipa", "language", "senses"]
        for field in required_fields:
            if field not in entry_data:
                issues.append(f"Entry {idx} ({entry.get('id', 'unknown')}): missing '{field}'")

        # Validate senses
        if "senses" in entry_data:
            senses = entry_data["senses"]

            if not isinstance(senses, list) or len(senses) == 0:
                issues.append(f"Entry {idx}: invalid or empty senses")
                continue

            for sense_idx, sense in enumerate(senses):
                required_sense_fields = ["sense_id", "definition", "ipa_hebrew", "hebrew", "pos"]

                for field in required_sense_fields:
                    if field not in sense:
                        issues.append(
                            f"Entry {idx}, sense {sense_idx}: missing '{field}'"
                        )

                # Validate sense_id
                if "sense_id" in sense and sense["sense_id"] < 1:
                    issues.append(f"Entry {idx}, sense {sense_idx}: invalid sense_id")

        # Validate language
        if entry_data.get("language") not in ["es", "he"]:
            issues.append(f"Entry {idx}: invalid language '{entry_data.get('language')}'")

    # Calculate quality metrics
    total_senses = sum(len(e["entry"]["senses"]) for e in entries if "entry" in e and "senses" in e["entry"])

    senses_with_ipa = sum(
        1 for e in entries if "entry" in e
        for s in e["entry"].get("senses", [])
        if s.get("ipa_hebrew") and s["ipa_hebrew"] not in ["", "None"]
    )

    ipa_coverage = (senses_with_ipa / total_senses * 100) if total_senses > 0 else 0

    logger.info(f"Dictionary quality metrics:")
    logger.info(f"  Total entries: {len(entries)}")
    logger.info(f"  Total senses: {total_senses}")
    logger.info(f"  Hebrew IPA coverage: {ipa_coverage:.1f}%")

    if ipa_coverage < 80:
        issues.append(f"Low IPA coverage: {ipa_coverage:.1f}% (expected >= 80%)")

    # Log issues
    if issues:
        logger.warning(f"Dictionary validation issues ({len(issues)} found):")
        for issue in issues[:20]:  # Show first 20
            logger.warning(f"  - {issue}")

        if len(issues) > 20:
            logger.warning(f"  ... and {len(issues) - 20} more")

        # Fail on critical structural issues
        critical_issues = [i for i in issues if "missing 'id'" in i or "missing 'entry'" in i]
        if len(critical_issues) > len(entries) * 0.01:  # More than 1%
            raise DataQualityError(f"Too many critical structural issues: {len(critical_issues)}")

    logger.info(f"✓ Validation passed for final dictionary")
    return entries


def generate_data_quality_report(
    enriched_df: pd.DataFrame
) -> Dict[str, Any]:
    """Generate comprehensive data quality report.

    Args:
        enriched_df: Enriched entries DataFrame

    Returns:
        Dictionary with quality metrics
    """
    logger.info("Generating data quality report...")

    report = {
        "total_entries": len(enriched_df),
        "timestamp": pd.Timestamp.now().isoformat(),
        "metrics": {},
        "issues": [],
        "recommendations": []
    }

    # Match type distribution
    if "match_type" in enriched_df.columns:
        match_dist = enriched_df["match_type"].value_counts().to_dict()
        report["metrics"]["match_type_distribution"] = match_dist

        direct_rate = match_dist.get("direct", 0) / len(enriched_df)
        if direct_rate < 0.5:
            report["issues"].append(f"Low direct match rate: {direct_rate:.1%}")
            report["recommendations"].append("Review Wiktionary translation links quality")

    # IPA coverage
    if "he_ipa" in enriched_df.columns:
        valid_ipa = enriched_df[
            (enriched_df["he_ipa"].notna()) &
            (enriched_df["he_ipa"] != "") &
            (enriched_df["he_ipa"].str.len() > 2)
        ]
        ipa_coverage = len(valid_ipa) / len(enriched_df)
        report["metrics"]["hebrew_ipa_coverage"] = ipa_coverage

        if ipa_coverage < 0.8:
            report["issues"].append(f"Low IPA coverage: {ipa_coverage:.1%}")
            report["recommendations"].append("Run IPA generation pipeline or check phonikud library")

    # Polysemy analysis
    if "es_word" in enriched_df.columns:
        polysemic = enriched_df.groupby("es_word").size()
        polysemic_words = (polysemic > 1).sum()
        max_senses = polysemic.max()
        avg_senses = polysemic.mean()

        report["metrics"]["polysemy"] = {
            "polysemic_words": int(polysemic_words),
            "max_senses": int(max_senses),
            "avg_senses": float(avg_senses)
        }

    # Duplicate check
    duplicates = enriched_df.duplicated(subset=["es_word", "he_word", "sense_id"], keep=False)
    dup_count = duplicates.sum()

    if dup_count > 0:
        report["metrics"]["duplicates"] = int(dup_count)
        report["issues"].append(f"Found {dup_count} duplicate alignments")
        report["recommendations"].append("Run deduplication step in pipeline")

    # Overall quality score (0-100)
    quality_score = 100.0

    if "hebrew_ipa_coverage" in report["metrics"]:
        ipa_penalty = (1 - report["metrics"]["hebrew_ipa_coverage"]) * 30
        quality_score -= ipa_penalty

    if dup_count > 0:
        dup_penalty = min((dup_count / len(enriched_df)) * 50, 20)
        quality_score -= dup_penalty

    report["overall_quality_score"] = max(0, quality_score)

    # Verdict
    if quality_score >= 90:
        report["verdict"] = "EXCELLENT"
    elif quality_score >= 75:
        report["verdict"] = "GOOD"
    elif quality_score >= 60:
        report["verdict"] = "ACCEPTABLE"
    else:
        report["verdict"] = "NEEDS_IMPROVEMENT"

    logger.info(f"Data quality score: {quality_score:.1f}/100 ({report['verdict']})")
    logger.info(f"Found {len(report['issues'])} issues")

    return report
