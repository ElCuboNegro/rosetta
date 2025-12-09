"""Statistics and visualization nodes for data processing pipeline.

This module provides nodes for tracking progress, computing statistics,
and creating visualizations that Kedro Viz can display in real-time.
"""

import logging
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Any
from collections import Counter

logger = logging.getLogger(__name__)


def compute_parsing_stats(
    spanish_entries: pd.DataFrame,
    hebrew_entries: pd.DataFrame,
    examples: pd.DataFrame
) -> Dict[str, Any]:
    """Compute statistics about parsed data.

    Args:
        spanish_entries: Parsed Spanish Wiktionary entries
        hebrew_entries: Parsed Hebrew Wiktionary entries
        examples: Processed Tatoeba examples

    Returns:
        Dictionary with comprehensive parsing statistics
    """
    logger.info("Computing parsing statistics...")

    # Spanish stats
    es_total = len(spanish_entries)
    es_with_ipa = spanish_entries['ipa'].notna().sum()
    es_with_translations = spanish_entries['translations_he'].apply(len).sum()
    es_pos_distribution = spanish_entries['pos'].value_counts().to_dict()
    es_avg_definitions = spanish_entries['definitions'].apply(len).mean()

    # Hebrew stats
    he_total = len(hebrew_entries)
    he_with_ipa = hebrew_entries['ipa'].notna().sum()
    he_with_translations = hebrew_entries['translations_es'].apply(len).sum()
    he_pos_distribution = hebrew_entries['pos'].value_counts().to_dict()
    he_avg_definitions = hebrew_entries['definitions'].apply(len).mean()

    # Examples stats
    ex_total = len(examples)
    ex_avg_es_words = examples['es_words'].apply(len).mean()
    ex_avg_he_words = examples['he_words'].apply(len).mean()

    stats = {
        "spanish": {
            "total_entries": int(es_total),
            "entries_with_ipa": int(es_with_ipa),
            "ipa_coverage_pct": round(es_with_ipa / es_total * 100, 2) if es_total > 0 else 0,
            "total_translations": int(es_with_translations),
            "avg_translations_per_entry": round(es_with_translations / es_total, 2) if es_total > 0 else 0,
            "avg_definitions_per_entry": round(es_avg_definitions, 2),
            "pos_distribution": es_pos_distribution
        },
        "hebrew": {
            "total_entries": int(he_total),
            "entries_with_ipa": int(he_with_ipa),
            "ipa_coverage_pct": round(he_with_ipa / he_total * 100, 2) if he_total > 0 else 0,
            "total_translations": int(he_with_translations),
            "avg_translations_per_entry": round(he_with_translations / he_total, 2) if he_total > 0 else 0,
            "avg_definitions_per_entry": round(he_avg_definitions, 2),
            "pos_distribution": he_pos_distribution
        },
        "examples": {
            "total_pairs": int(ex_total),
            "avg_spanish_words": round(ex_avg_es_words, 2),
            "avg_hebrew_words": round(ex_avg_he_words, 2)
        }
    }

    logger.info(f"Spanish: {es_total} entries, {es_with_ipa} with IPA ({stats['spanish']['ipa_coverage_pct']}%)")
    logger.info(f"Hebrew: {he_total} entries, {he_with_ipa} with IPA ({stats['hebrew']['ipa_coverage_pct']}%)")
    logger.info(f"Examples: {ex_total} sentence pairs")

    return stats


def create_parsing_visualizations(stats: Dict[str, Any]) -> go.Figure:
    """Create visualization charts for parsing statistics.

    Args:
        stats: Statistics from compute_parsing_stats

    Returns:
        Plotly figure with multiple subplots showing parsing statistics
    """
    logger.info("Creating parsing visualizations...")

    from plotly.subplots import make_subplots

    # Create subplots: 2 rows, 2 columns
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            'Entry Counts by Language',
            'IPA Coverage',
            'Spanish POS Distribution',
            'Hebrew POS Distribution'
        ),
        specs=[
            [{"type": "bar"}, {"type": "bar"}],
            [{"type": "pie"}, {"type": "pie"}]
        ]
    )

    # 1. Entry counts
    fig.add_trace(
        go.Bar(
            x=['Spanish', 'Hebrew', 'Examples'],
            y=[
                stats['spanish']['total_entries'],
                stats['hebrew']['total_entries'],
                stats['examples']['total_pairs']
            ],
            marker_color=['#FF6B6B', '#4ECDC4', '#95E1D3'],
            name='Entries'
        ),
        row=1, col=1
    )

    # 2. IPA Coverage
    fig.add_trace(
        go.Bar(
            x=['Spanish', 'Hebrew'],
            y=[
                stats['spanish']['ipa_coverage_pct'],
                stats['hebrew']['ipa_coverage_pct']
            ],
            marker_color=['#FF6B6B', '#4ECDC4'],
            name='IPA Coverage %',
            text=[
                f"{stats['spanish']['ipa_coverage_pct']}%",
                f"{stats['hebrew']['ipa_coverage_pct']}%"
            ],
            textposition='auto'
        ),
        row=1, col=2
    )

    # 3. Spanish POS Distribution
    es_pos = stats['spanish']['pos_distribution']
    if es_pos:
        fig.add_trace(
            go.Pie(
                labels=list(es_pos.keys())[:10],  # Top 10
                values=list(es_pos.values())[:10],
                name='Spanish POS'
            ),
            row=2, col=1
        )

    # 4. Hebrew POS Distribution
    he_pos = stats['hebrew']['pos_distribution']
    if he_pos:
        fig.add_trace(
            go.Pie(
                labels=list(he_pos.keys())[:10],  # Top 10
                values=list(he_pos.values())[:10],
                name='Hebrew POS'
            ),
            row=2, col=2
        )

    fig.update_layout(
        title_text="Data Processing Pipeline Statistics",
        showlegend=False,
        height=800
    )

    return fig


def compute_alignment_stats(
    aligned_matches: pd.DataFrame,
    enriched_entries: pd.DataFrame
) -> Dict[str, Any]:
    """Compute statistics about alignment quality.

    Args:
        aligned_matches: Aligned Spanish-Hebrew word pairs
        enriched_entries: Enriched entries with examples

    Returns:
        Dictionary with alignment statistics
    """
    logger.info("Computing alignment statistics...")

    total_alignments = len(aligned_matches)
    unique_es_words = aligned_matches['es_word'].nunique()
    unique_he_words = aligned_matches['he_word'].nunique()

    # Polysemy analysis
    es_polysemy = aligned_matches.groupby('es_word').size()
    avg_senses_per_word = es_polysemy.mean()
    max_senses = es_polysemy.max()
    polysemic_words = (es_polysemy > 1).sum()

    # Enrichment stats
    total_enriched = len(enriched_entries)
    entries_with_examples = enriched_entries['examples'].apply(lambda x: len(x) > 0).sum()
    total_examples = enriched_entries['examples'].apply(len).sum()
    avg_examples_per_entry = enriched_entries['examples'].apply(len).mean()

    # POS distribution in alignments
    pos_counts = aligned_matches['es_pos'].value_counts().to_dict()

    stats = {
        "alignment": {
            "total_alignments": int(total_alignments),
            "unique_spanish_words": int(unique_es_words),
            "unique_hebrew_words": int(unique_he_words),
            "avg_translations_per_word": round(total_alignments / unique_es_words, 2) if unique_es_words > 0 else 0
        },
        "polysemy": {
            "avg_senses_per_word": round(avg_senses_per_word, 2),
            "max_senses": int(max_senses),
            "polysemic_words_count": int(polysemic_words),
            "polysemic_words_pct": round(polysemic_words / unique_es_words * 100, 2) if unique_es_words > 0 else 0
        },
        "enrichment": {
            "total_enriched": int(total_enriched),
            "entries_with_examples": int(entries_with_examples),
            "example_coverage_pct": round(entries_with_examples / total_enriched * 100, 2) if total_enriched > 0 else 0,
            "total_examples": int(total_examples),
            "avg_examples_per_entry": round(avg_examples_per_entry, 2)
        },
        "pos_distribution": pos_counts
    }

    logger.info(f"Aligned: {total_alignments} pairs, {unique_es_words} Spanish words, {unique_he_words} Hebrew words")
    logger.info(f"Polysemy: {polysemic_words} words with multiple senses (avg: {avg_senses_per_word:.2f})")
    logger.info(f"Examples: {entries_with_examples}/{total_enriched} entries enriched ({stats['enrichment']['example_coverage_pct']}%)")

    return stats


def create_alignment_visualizations(stats: Dict[str, Any]) -> go.Figure:
    """Create visualization charts for alignment statistics.

    Args:
        stats: Statistics from compute_alignment_stats

    Returns:
        Plotly figure with alignment visualizations
    """
    logger.info("Creating alignment visualizations...")

    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            'Alignment Overview',
            'Polysemy Analysis',
            'Example Coverage',
            'POS Distribution in Alignments'
        ),
        specs=[
            [{"type": "bar"}, {"type": "bar"}],
            [{"type": "indicator"}, {"type": "pie"}]
        ]
    )

    # 1. Alignment Overview
    fig.add_trace(
        go.Bar(
            x=['Total Alignments', 'Spanish Words', 'Hebrew Words'],
            y=[
                stats['alignment']['total_alignments'],
                stats['alignment']['unique_spanish_words'],
                stats['alignment']['unique_hebrew_words']
            ],
            marker_color=['#A8E6CF', '#FFD3B6', '#FFAAA5'],
            name='Counts'
        ),
        row=1, col=1
    )

    # 2. Polysemy Analysis
    fig.add_trace(
        go.Bar(
            x=['Monosemic', 'Polysemic'],
            y=[
                stats['alignment']['unique_spanish_words'] - stats['polysemy']['polysemic_words_count'],
                stats['polysemy']['polysemic_words_count']
            ],
            marker_color=['#95E1D3', '#F38181'],
            name='Word Types',
            text=[
                f"{100 - stats['polysemy']['polysemic_words_pct']:.1f}%",
                f"{stats['polysemy']['polysemic_words_pct']:.1f}%"
            ],
            textposition='auto'
        ),
        row=1, col=2
    )

    # 3. Example Coverage Indicator
    fig.add_trace(
        go.Indicator(
            mode="gauge+number+delta",
            value=stats['enrichment']['example_coverage_pct'],
            title={'text': "Example Coverage %"},
            delta={'reference': 50},
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': "#4ECDC4"},
                'steps': [
                    {'range': [0, 30], 'color': "#FFE5E5"},
                    {'range': [30, 70], 'color': "#FFF4E5"},
                    {'range': [70, 100], 'color': "#E5FFE5"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 80
                }
            }
        ),
        row=2, col=1
    )

    # 4. POS Distribution
    pos_dist = stats['pos_distribution']
    if pos_dist:
        top_pos = dict(sorted(pos_dist.items(), key=lambda x: x[1], reverse=True)[:10])
        fig.add_trace(
            go.Pie(
                labels=list(top_pos.keys()),
                values=list(top_pos.values()),
                name='POS'
            ),
            row=2, col=2
        )

    fig.update_layout(
        title_text="Alignment & Enrichment Statistics",
        showlegend=False,
        height=800
    )

    return fig


def create_progress_summary(
    parsing_stats: Dict[str, Any],
    alignment_stats: Dict[str, Any]
) -> Dict[str, Any]:
    """Create overall progress summary for the entire pipeline.

    Args:
        parsing_stats: Statistics from parsing phase
        alignment_stats: Statistics from alignment phase

    Returns:
        Comprehensive progress summary
    """
    logger.info("Creating progress summary...")

    summary = {
        "pipeline_overview": {
            "total_spanish_entries": parsing_stats['spanish']['total_entries'],
            "total_hebrew_entries": parsing_stats['hebrew']['total_entries'],
            "total_alignments": alignment_stats['alignment']['total_alignments'],
            "final_dictionary_size": alignment_stats['alignment']['unique_spanish_words']
        },
        "data_quality": {
            "spanish_ipa_coverage": parsing_stats['spanish']['ipa_coverage_pct'],
            "hebrew_ipa_coverage": parsing_stats['hebrew']['ipa_coverage_pct'],
            "example_coverage": alignment_stats['enrichment']['example_coverage_pct'],
            "avg_examples_per_entry": alignment_stats['enrichment']['avg_examples_per_entry']
        },
        "linguistic_features": {
            "polysemic_words": alignment_stats['polysemy']['polysemic_words_count'],
            "polysemy_rate": alignment_stats['polysemy']['polysemic_words_pct'],
            "avg_senses_per_word": alignment_stats['polysemy']['avg_senses_per_word'],
            "max_senses_for_word": alignment_stats['polysemy']['max_senses']
        }
    }

    logger.info("=" * 60)
    logger.info("PIPELINE PROGRESS SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Input: {summary['pipeline_overview']['total_spanish_entries']} Spanish + {summary['pipeline_overview']['total_hebrew_entries']} Hebrew entries")
    logger.info(f"Output: {summary['pipeline_overview']['final_dictionary_size']} dictionary entries with {summary['pipeline_overview']['total_alignments']} senses")
    logger.info(f"Quality: {summary['data_quality']['spanish_ipa_coverage']:.1f}% ES IPA, {summary['data_quality']['hebrew_ipa_coverage']:.1f}% HE IPA, {summary['data_quality']['example_coverage']:.1f}% examples")
    logger.info(f"Polysemy: {summary['linguistic_features']['polysemic_words']} polysemic words ({summary['linguistic_features']['polysemy_rate']:.1f}%)")
    logger.info("=" * 60)

    return summary
