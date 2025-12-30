"""
Interactive web UI for reviewing and correcting sense clusters.

Usage:
    python scripts/cluster_review_ui.py

Then open http://localhost:5000 in your browser.
"""
import json
import logging
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, render_template_string, request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global data
clusters_df = None
current_word = None
corrections = {}


def load_clusters(filepath="data/04_feature/sense_clusters.parquet"):
    """Load sense clusters from parquet file."""
    global clusters_df
    clusters_df = pd.read_parquet(filepath)
    logger.info(f"Loaded {len(clusters_df)} cluster entries")
    return clusters_df


def get_unique_words():
    """Get list of all unique words in the dataset."""
    if clusters_df is None:
        return []
    return sorted(clusters_df['source_word'].unique().tolist())


def get_clusters_for_word(word):
    """Get all clusters for a specific word."""
    if clusters_df is None:
        return []

    word_data = clusters_df[clusters_df['source_word'] == word].copy()

    # Group by cluster ID
    clusters = []
    for cluster_id in sorted(word_data['sense_cluster_id'].unique()):
        cluster_examples = word_data[word_data['sense_cluster_id'] == cluster_id]

        clusters.append({
            'cluster_id': int(cluster_id),
            'size': len(cluster_examples),
            'examples': cluster_examples[['sentence_text', 'corpus_source']].to_dict('records'),
            'quality_score': cluster_examples['cluster_quality_score'].iloc[0] if 'cluster_quality_score' in cluster_examples.columns else None,
            'method': cluster_examples['clustering_method'].iloc[0] if 'clustering_method' in cluster_examples.columns else None,
        })

    return clusters


def search_sentences(query, language='both', max_results=100):
    """Search for sentences containing the query in Spanish or Hebrew.

    Args:
        query: Search term
        language: 'spanish', 'hebrew', or 'both'
        max_results: Maximum number of results to return

    Returns:
        List of matching results with word, cluster, and sentence info
    """
    if clusters_df is None or not query:
        return []

    query = query.strip().lower()
    results = []

    for idx, row in clusters_df.iterrows():
        match_found = False
        match_field = None

        # Search in Spanish sentence
        if language in ['spanish', 'both']:
            sentence_text = str(row.get('sentence_text', '')).lower()
            if query in sentence_text:
                match_found = True
                match_field = 'spanish'

        # Search in Hebrew (target) sentence if available
        if language in ['hebrew', 'both'] and not match_found:
            # Check common Hebrew field names
            for hebrew_field in ['target_text', 'target_he', 'hebrew_text', 'translation']:
                if hebrew_field in row and pd.notna(row[hebrew_field]):
                    hebrew_text = str(row[hebrew_field]).lower()
                    if query in hebrew_text:
                        match_found = True
                        match_field = 'hebrew'
                        break

        if match_found:
            results.append({
                'word': row['source_word'],
                'cluster_id': int(row['sense_cluster_id']),
                'sentence': row['sentence_text'],
                'hebrew': row.get('target_text', row.get('target_he', '')),
                'source': row.get('corpus_source', 'unknown'),
                'match_field': match_field,
                'quality_score': row.get('cluster_quality_score')
            })

            if len(results) >= max_results:
                break

    return results


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Sense Cluster Review</title>
    <meta charset="UTF-8">
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { color: #333; margin-bottom: 10px; }
        .subtitle { color: #666; margin-bottom: 30px; }

        .controls {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .control-section {
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 1px solid #eee;
        }
        .control-section:last-child {
            margin-bottom: 0;
            padding-bottom: 0;
            border-bottom: none;
        }
        .control-section h3 {
            margin: 0 0 10px 0;
            font-size: 14px;
            color: #666;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .word-selector { display: flex; gap: 10px; align-items: center; }
        .word-selector select {
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
        }
        .word-selector button {
            padding: 10px 20px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        .word-selector button:hover { background: #0056b3; }

        .search-bar {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .search-bar input[type="text"] {
            flex: 1;
            padding: 10px 15px;
            border: 2px solid #007bff;
            border-radius: 4px;
            font-size: 16px;
        }
        .search-bar select {
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        .search-bar button {
            padding: 10px 20px;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
        }
        .search-bar button:hover { background: #218838; }
        .btn-clear-search {
            background: #6c757d !important;
        }
        .btn-clear-search:hover {
            background: #5a6268 !important;
        }

        .search-results {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .search-results h2 {
            margin: 0 0 15px 0;
            font-size: 18px;
            color: #333;
        }
        .search-result-item {
            padding: 15px;
            margin-bottom: 10px;
            background: #f8f9fa;
            border-radius: 4px;
            border-left: 4px solid #007bff;
            cursor: pointer;
            transition: all 0.2s;
        }
        .search-result-item:hover {
            background: #e9ecef;
            transform: translateX(5px);
        }
        .search-result-word {
            font-weight: 700;
            color: #007bff;
            font-size: 16px;
            margin-bottom: 5px;
        }
        .search-result-cluster {
            font-size: 12px;
            color: #666;
            margin-bottom: 8px;
        }
        .search-result-text {
            font-size: 14px;
            color: #333;
            line-height: 1.6;
            margin-bottom: 5px;
        }
        .search-result-hebrew {
            font-size: 14px;
            color: #666;
            direction: rtl;
            text-align: right;
            margin-bottom: 5px;
        }
        .search-result-source {
            font-size: 11px;
            color: #999;
            text-transform: uppercase;
        }
        .search-highlight {
            background: #fff3cd;
            padding: 2px 4px;
            border-radius: 2px;
            font-weight: 600;
        }
        .search-stats {
            padding: 10px;
            background: #e7f3ff;
            border-radius: 4px;
            margin-bottom: 15px;
            font-size: 14px;
            color: #004085;
        }

        .clusters-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .cluster {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            position: relative;
        }
        .cluster.dragging { opacity: 0.5; }
        .cluster.drag-over {
            border: 2px dashed #007bff;
            background: #e7f3ff;
        }

        .cluster-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #eee;
        }
        .cluster-title {
            font-size: 18px;
            font-weight: bold;
            color: #333;
        }
        .cluster-info {
            font-size: 12px;
            color: #666;
        }
        .quality-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: bold;
        }
        .quality-high { background: #d4edda; color: #155724; }
        .quality-medium { background: #fff3cd; color: #856404; }
        .quality-low { background: #f8d7da; color: #721c24; }

        .cluster-label {
            margin-bottom: 15px;
        }
        .cluster-label input {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        .cluster-label label {
            display: block;
            margin-bottom: 5px;
            font-size: 12px;
            color: #666;
            font-weight: 600;
        }

        .cluster-meaning {
            margin-bottom: 15px;
            padding: 12px;
            background: #f8f9fa;
            border-radius: 4px;
            border: 1px solid #e9ecef;
        }
        .btn-edit-meaning {
            padding: 6px 12px;
            background: #6c757d;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
            margin-bottom: 8px;
        }
        .btn-edit-meaning:hover {
            background: #5a6268;
        }
        .meaning-preview {
            font-size: 13px;
            color: #495057;
            line-height: 1.6;
        }
        .meaning-preview em {
            color: #999;
        }
        .meaning-preview .definition {
            font-weight: 600;
            margin-bottom: 5px;
        }
        .meaning-preview .usage {
            color: #666;
            font-style: italic;
        }

        .example {
            padding: 12px;
            margin-bottom: 8px;
            background: #f8f9fa;
            border-radius: 4px;
            cursor: move;
            border-left: 3px solid #007bff;
            transition: all 0.2s;
        }
        .example:hover {
            background: #e9ecef;
            transform: translateX(5px);
        }
        .example.dragging {
            opacity: 0.5;
            transform: rotate(2deg);
        }
        .example-text {
            font-size: 14px;
            line-height: 1.6;
            color: #333;
            margin-bottom: 5px;
        }
        .example-source {
            font-size: 11px;
            color: #999;
            text-transform: uppercase;
            font-weight: 600;
        }

        .add-cluster-btn {
            background: white;
            border: 2px dashed #007bff;
            color: #007bff;
            padding: 40px;
            text-align: center;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            transition: all 0.2s;
        }
        .add-cluster-btn:hover {
            background: #e7f3ff;
            border-color: #0056b3;
            color: #0056b3;
        }

        .actions {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .actions button {
            padding: 12px 30px;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
            font-weight: 600;
        }
        .btn-save {
            background: #28a745;
            color: white;
        }
        .btn-save:hover { background: #218838; }
        .btn-reset {
            background: #6c757d;
            color: white;
        }
        .btn-reset:hover { background: #5a6268; }
        .btn-export {
            background: #17a2b8;
            color: white;
        }
        .btn-export:hover { background: #138496; }

        .message {
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
            display: none;
        }
        .message.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .message.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }

        /* Modal styles */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            animation: fadeIn 0.2s;
        }
        .modal.active {
            display: flex;
            align-items: center;
            justify-content: center;
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        .modal-content {
            background: white;
            padding: 30px;
            border-radius: 8px;
            width: 90%;
            max-width: 700px;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            animation: slideUp 0.3s;
        }
        @keyframes slideUp {
            from {
                transform: translateY(30px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #eee;
        }
        .modal-header h2 {
            margin: 0;
            color: #333;
        }
        .modal-close {
            background: none;
            border: none;
            font-size: 28px;
            cursor: pointer;
            color: #999;
            line-height: 1;
            padding: 0;
            width: 30px;
            height: 30px;
        }
        .modal-close:hover {
            color: #333;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
            font-size: 14px;
        }
        .form-group input,
        .form-group textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            font-family: inherit;
        }
        .form-group textarea {
            resize: vertical;
            min-height: 80px;
        }
        .form-group .hint {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
            font-style: italic;
        }
        .modal-actions {
            display: flex;
            justify-content: flex-end;
            gap: 10px;
            margin-top: 25px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }
        .modal-actions button {
            padding: 10px 24px;
            border: none;
            border-radius: 4px;
            font-size: 14px;
            cursor: pointer;
            font-weight: 600;
        }
        .btn-cancel {
            background: #6c757d;
            color: white;
        }
        .btn-cancel:hover {
            background: #5a6268;
        }
        .btn-confirm {
            background: #007bff;
            color: white;
        }
        .btn-confirm:hover {
            background: #0056b3;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 Sense Cluster Review Tool</h1>
        <p class="subtitle">Search for words in Spanish or Hebrew, or browse words from the dropdown</p>

        <div class="controls">
            <div class="control-section">
                <h3>🔍 Search</h3>
                <div class="search-bar">
                    <input type="text"
                           id="search-input"
                           placeholder="Search for Spanish or Hebrew text..."
                           onkeypress="if(event.key==='Enter') searchSentences()">
                    <select id="search-language">
                        <option value="both">Both</option>
                        <option value="spanish">Spanish Only</option>
                        <option value="hebrew">Hebrew Only</option>
                    </select>
                    <button onclick="searchSentences()">🔍 Search</button>
                    <button class="btn-clear-search" onclick="clearSearch()">Clear</button>
                </div>
            </div>

            <div class="control-section">
                <h3>📖 Browse Words</h3>
                <div class="word-selector">
                    <label for="word-select" style="font-weight: 600; min-width: 100px;">Select Word:</label>
                    <select id="word-select">
                        <option value="">-- Choose a word --</option>
                    </select>
                    <button onclick="loadWord()">Load</button>
                </div>
            </div>
        </div>

        <div id="message" class="message"></div>

        <div id="search-results-area" style="display: none;"></div>

        <div id="clusters-area">
            <p style="text-align: center; color: #999; padding: 40px;">Search for text or select a word to review its clusters</p>
        </div>

        <div class="actions" id="actions-bar" style="display: none;">
            <div>
                <span id="changes-count" style="color: #666; font-weight: 600;">No changes</span>
            </div>
            <div style="display: flex; gap: 10px;">
                <button class="btn-reset" onclick="resetChanges()">Reset</button>
                <button class="btn-export" onclick="exportCorrections()">Export JSON</button>
                <button class="btn-save" onclick="saveCorrections()">Save Changes</button>
            </div>
        </div>
    </div>

    <!-- Meaning Editor Modal -->
    <div id="meaning-modal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>Edit Sense Meaning</h2>
                <button class="modal-close" onclick="closeMeaningEditor()">&times;</button>
            </div>

            <div class="form-group">
                <label for="meaning-label">Sense Label *</label>
                <input type="text"
                       id="meaning-label"
                       placeholder="e.g., 'to pretend', 'to court', 'to intend'">
                <div class="hint">Short label identifying this sense</div>
            </div>

            <div class="form-group">
                <label for="meaning-definition">Definition *</label>
                <textarea id="meaning-definition"
                          placeholder="e.g., 'To behave as if something is true when it is not'"></textarea>
                <div class="hint">Clear, concise definition of this sense</div>
            </div>

            <div class="form-group">
                <label for="meaning-usage">Usage Notes</label>
                <textarea id="meaning-usage"
                          placeholder="e.g., 'Used with que + subjunctive'"></textarea>
                <div class="hint">Grammar, register, or usage information (optional)</div>
            </div>

            <div class="form-group">
                <label for="meaning-examples">Example Sentences</label>
                <textarea id="meaning-examples"
                          placeholder="One example per line&#10;e.g., Pretendió que todo estaba bien&#10;     She pretended everything was fine"></textarea>
                <div class="hint">One example per line, with optional translations (optional)</div>
            </div>

            <div class="form-group">
                <label for="meaning-notes">Additional Notes</label>
                <textarea id="meaning-notes"
                          placeholder="e.g., 'Common in literary contexts'"></textarea>
                <div class="hint">Any other relevant information (optional)</div>
            </div>

            <div class="modal-actions">
                <button class="btn-cancel" onclick="closeMeaningEditor()">Cancel</button>
                <button class="btn-confirm" onclick="saveMeaning()">Save Meaning</button>
            </div>
        </div>
    </div>

    <script>
        let currentWord = null;
        let clusters = [];
        let changes = new Map(); // example_text -> new_cluster_id
        let clusterLabels = new Map(); // cluster_id -> label
        let clusterMeanings = new Map(); // cluster_id -> {definition, examples, notes}
        let nextClusterId = 1000; // For new clusters

        // Load word list
        fetch('/api/words')
            .then(r => r.json())
            .then(words => {
                const select = document.getElementById('word-select');
                words.forEach(word => {
                    const option = document.createElement('option');
                    option.value = word;
                    option.textContent = word;
                    select.appendChild(option);
                });
            });

        function searchSentences() {
            const query = document.getElementById('search-input').value.trim();
            if (!query) {
                showMessage('Please enter a search term', 'error');
                return;
            }

            const language = document.getElementById('search-language').value;

            fetch(`/api/search?query=${encodeURIComponent(query)}&language=${language}`)
                .then(r => r.json())
                .then(results => {
                    displaySearchResults(results, query);
                })
                .catch(err => {
                    showMessage('Search failed: ' + err, 'error');
                });
        }

        function displaySearchResults(results, query) {
            const area = document.getElementById('search-results-area');

            if (results.length === 0) {
                area.innerHTML = `
                    <div class="search-results">
                        <h2>No results found for "${query}"</h2>
                        <p style="color: #666;">Try a different search term or language filter.</p>
                    </div>
                `;
                area.style.display = 'block';
                document.getElementById('clusters-area').style.display = 'none';
                return;
            }

            // Group results by word
            const byWord = {};
            results.forEach(r => {
                if (!byWord[r.word]) byWord[r.word] = [];
                byWord[r.word].push(r);
            });

            const uniqueWords = Object.keys(byWord).length;

            let html = `
                <div class="search-results">
                    <h2>🔍 Search Results for "${query}"</h2>
                    <div class="search-stats">
                        Found <strong>${results.length}</strong> matches across <strong>${uniqueWords}</strong> word${uniqueWords > 1 ? 's' : ''}
                    </div>
            `;

            results.forEach(result => {
                // Highlight the query in the text
                const highlightedSpanish = highlightText(result.sentence, query);
                const highlightedHebrew = result.hebrew ? highlightText(result.hebrew, query) : '';

                html += `
                    <div class="search-result-item" onclick="loadWordFromSearch('${result.word}')">
                        <div class="search-result-word">${result.word}</div>
                        <div class="search-result-cluster">
                            Cluster ${result.cluster_id}
                            ${result.quality_score !== null ? `
                                • Quality: ${(result.quality_score * 100).toFixed(0)}%
                            ` : ''}
                            • ${result.source}
                        </div>
                        <div class="search-result-text">${highlightedSpanish}</div>
                        ${highlightedHebrew ? `<div class="search-result-hebrew">${highlightedHebrew}</div>` : ''}
                    </div>
                `;
            });

            html += '</div>';
            area.innerHTML = html;
            area.style.display = 'block';
            document.getElementById('clusters-area').style.display = 'none';
        }

        function highlightText(text, query) {
            if (!text || !query) return text;

            const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
            return text.replace(regex, '<span class="search-highlight">$1</span>');
        }

        function escapeRegex(str) {
            return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        }

        function loadWordFromSearch(word) {
            // Clear search results and load the word
            clearSearch();
            document.getElementById('word-select').value = word;
            loadWord();
        }

        function clearSearch() {
            document.getElementById('search-input').value = '';
            document.getElementById('search-results-area').style.display = 'none';
            document.getElementById('clusters-area').style.display = 'block';
        }

        function loadWord() {
            const word = document.getElementById('word-select').value;
            if (!word) return;

            currentWord = word;
            changes.clear();
            clusterLabels.clear();
            clusterMeanings.clear();

            // Hide search results
            document.getElementById('search-results-area').style.display = 'none';
            document.getElementById('clusters-area').style.display = 'block';

            fetch(`/api/clusters/${word}`)
                .then(r => r.json())
                .then(data => {
                    clusters = data;
                    nextClusterId = Math.max(...clusters.map(c => c.cluster_id)) + 1;

                    // Load existing meanings if any
                    loadExistingMeanings(word);

                    renderClusters();
                    document.getElementById('actions-bar').style.display = 'flex';
                    updateChangesCount();
                });
        }

        function renderClusters() {
            const area = document.getElementById('clusters-area');
            area.innerHTML = '';

            const container = document.createElement('div');
            container.className = 'clusters-container';

            clusters.forEach(cluster => {
                container.appendChild(createClusterElement(cluster));
            });

            // Add "New Cluster" button
            const addBtn = document.createElement('div');
            addBtn.className = 'add-cluster-btn';
            addBtn.textContent = '+ Add New Cluster';
            addBtn.onclick = addNewCluster;
            container.appendChild(addBtn);

            area.appendChild(container);
        }

        function createClusterElement(cluster) {
            const div = document.createElement('div');
            div.className = 'cluster';
            div.dataset.clusterId = cluster.cluster_id;

            // Quality badge
            let qualityClass = 'quality-low';
            if (cluster.quality_score > 0.6) qualityClass = 'quality-high';
            else if (cluster.quality_score > 0.3) qualityClass = 'quality-medium';

            div.innerHTML = `
                <div class="cluster-header">
                    <div>
                        <div class="cluster-title">Cluster ${cluster.cluster_id}</div>
                        <div class="cluster-info">
                            ${cluster.size} examples
                            ${cluster.quality_score !== null ? `
                                <span class="quality-badge ${qualityClass}">
                                    Quality: ${(cluster.quality_score * 100).toFixed(0)}%
                                </span>
                            ` : ''}
                        </div>
                    </div>
                </div>
                <div class="cluster-label">
                    <label>Sense Label:</label>
                    <input type="text"
                           class="label-input"
                           placeholder="e.g., 'to pretend', 'to court', 'to intend'"
                           data-cluster-id="${cluster.cluster_id}"
                           oninput="updateClusterLabel(${cluster.cluster_id}, this.value)">
                </div>
                <div class="cluster-meaning">
                    <button class="btn-edit-meaning" onclick="openMeaningEditor(${cluster.cluster_id})">
                        ✏️ Edit Meaning
                    </button>
                    <div class="meaning-preview" id="meaning-preview-${cluster.cluster_id}">
                        <em>No meaning defined yet</em>
                    </div>
                </div>
                <div class="examples" id="cluster-${cluster.cluster_id}"></div>
            `;

            const examplesDiv = div.querySelector('.examples');
            cluster.examples.forEach((ex, idx) => {
                examplesDiv.appendChild(createExampleElement(ex, cluster.cluster_id));
            });

            // Drag and drop handlers
            div.addEventListener('dragover', handleDragOver);
            div.addEventListener('drop', handleDrop);
            div.addEventListener('dragleave', handleDragLeave);

            return div;
        }

        function createExampleElement(example, clusterId) {
            const div = document.createElement('div');
            div.className = 'example';
            div.draggable = true;
            div.dataset.sentence = example.sentence_text;
            div.dataset.originalCluster = clusterId;

            div.innerHTML = `
                <div class="example-text">${example.sentence_text}</div>
                <div class="example-source">${example.corpus_source}</div>
            `;

            div.addEventListener('dragstart', handleDragStart);
            div.addEventListener('dragend', handleDragEnd);

            return div;
        }

        function addNewCluster() {
            const newCluster = {
                cluster_id: nextClusterId++,
                size: 0,
                examples: [],
                quality_score: null,
                method: 'manual'
            };
            clusters.push(newCluster);
            renderClusters();
        }

        function updateClusterLabel(clusterId, label) {
            clusterLabels.set(clusterId, label);
            updateChangesCount();
        }

        let currentEditingClusterId = null;

        function loadExistingMeanings(word) {
            // Try to load previously saved meanings from server
            fetch(`/api/meanings/${word}`)
                .then(r => r.json())
                .then(meanings => {
                    if (meanings) {
                        for (const [clusterId, meaning] of Object.entries(meanings)) {
                            clusterMeanings.set(parseInt(clusterId), meaning);
                            updateMeaningPreview(parseInt(clusterId));
                        }
                    }
                })
                .catch(err => {
                    console.log('No existing meanings found');
                });
        }

        function openMeaningEditor(clusterId) {
            currentEditingClusterId = clusterId;

            // Load existing meaning if any
            const existing = clusterMeanings.get(clusterId) || {};
            const label = clusterLabels.get(clusterId) || '';

            document.getElementById('meaning-label').value = label || existing.label || '';
            document.getElementById('meaning-definition').value = existing.definition || '';
            document.getElementById('meaning-usage').value = existing.usage || '';
            document.getElementById('meaning-examples').value = existing.examples || '';
            document.getElementById('meaning-notes').value = existing.notes || '';

            document.getElementById('meaning-modal').classList.add('active');
        }

        function closeMeaningEditor() {
            document.getElementById('meaning-modal').classList.remove('active');
            currentEditingClusterId = null;
        }

        function saveMeaning() {
            const label = document.getElementById('meaning-label').value.trim();
            const definition = document.getElementById('meaning-definition').value.trim();

            if (!label || !definition) {
                alert('Please provide at least a label and definition');
                return;
            }

            const meaning = {
                label: label,
                definition: definition,
                usage: document.getElementById('meaning-usage').value.trim(),
                examples: document.getElementById('meaning-examples').value.trim(),
                notes: document.getElementById('meaning-notes').value.trim()
            };

            clusterMeanings.set(currentEditingClusterId, meaning);
            clusterLabels.set(currentEditingClusterId, label); // Sync label

            // Update label input
            const labelInput = document.querySelector(`input[data-cluster-id="${currentEditingClusterId}"]`);
            if (labelInput) {
                labelInput.value = label;
            }

            updateMeaningPreview(currentEditingClusterId);
            updateChangesCount();
            closeMeaningEditor();
        }

        function updateMeaningPreview(clusterId) {
            const meaning = clusterMeanings.get(clusterId);
            const preview = document.getElementById(`meaning-preview-${clusterId}`);

            if (!preview) return;

            if (!meaning) {
                preview.innerHTML = '<em>No meaning defined yet</em>';
                return;
            }

            let html = '';
            if (meaning.definition) {
                html += `<div class="definition">${meaning.definition}</div>`;
            }
            if (meaning.usage) {
                html += `<div class="usage">${meaning.usage}</div>`;
            }

            preview.innerHTML = html || '<em>No meaning defined yet</em>';
        }

        // Close modal when clicking outside
        document.getElementById('meaning-modal').addEventListener('click', function(e) {
            if (e.target === this) {
                closeMeaningEditor();
            }
        });

        let draggedElement = null;

        function handleDragStart(e) {
            draggedElement = e.target;
            e.target.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
        }

        function handleDragEnd(e) {
            e.target.classList.remove('dragging');
        }

        function handleDragOver(e) {
            if (e.preventDefault) {
                e.preventDefault();
            }
            e.dataTransfer.dropEffect = 'move';
            e.currentTarget.classList.add('drag-over');
            return false;
        }

        function handleDragLeave(e) {
            e.currentTarget.classList.remove('drag-over');
        }

        function handleDrop(e) {
            if (e.stopPropagation) {
                e.stopPropagation();
            }
            e.currentTarget.classList.remove('drag-over');

            if (!draggedElement) return false;

            const targetCluster = e.currentTarget;
            const targetClusterId = parseInt(targetCluster.dataset.clusterId);
            const sentence = draggedElement.dataset.sentence;
            const originalCluster = parseInt(draggedElement.dataset.originalCluster);

            if (targetClusterId !== originalCluster) {
                // Record the change
                changes.set(sentence, targetClusterId);

                // Move the element visually
                const examplesDiv = targetCluster.querySelector('.examples');
                examplesDiv.appendChild(draggedElement);

                updateChangesCount();
            }

            return false;
        }

        function updateChangesCount() {
            const count = changes.size + clusterLabels.size + clusterMeanings.size;
            const span = document.getElementById('changes-count');
            if (count === 0) {
                span.textContent = 'No changes';
                span.style.color = '#666';
            } else {
                span.textContent = `${count} change${count > 1 ? 's' : ''}`;
                span.style.color = '#007bff';
            }
        }

        function resetChanges() {
            if (!confirm('Reset all changes?')) return;
            changes.clear();
            clusterLabels.clear();
            clusterMeanings.clear();
            loadWord();
        }

        function exportCorrections() {
            const corrections = {
                word: currentWord,
                changes: Object.fromEntries(changes),
                labels: Object.fromEntries(clusterLabels),
                meanings: Object.fromEntries(clusterMeanings),
                timestamp: new Date().toISOString()
            };

            const blob = new Blob([JSON.stringify(corrections, null, 2)], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `corrections_${currentWord}_${Date.now()}.json`;
            a.click();
        }

        function saveCorrections() {
            const corrections = {
                word: currentWord,
                changes: Object.fromEntries(changes),
                labels: Object.fromEntries(clusterLabels),
                meanings: Object.fromEntries(clusterMeanings)
            };

            fetch('/api/save', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(corrections)
            })
            .then(r => r.json())
            .then(result => {
                showMessage(result.message, 'success');
                changes.clear();
                clusterLabels.clear();
                // Keep meanings after save (they're part of the word definition)
                updateChangesCount();
            })
            .catch(err => {
                showMessage('Error saving corrections: ' + err, 'error');
            });
        }

        function showMessage(text, type) {
            const msg = document.getElementById('message');
            msg.textContent = text;
            msg.className = `message ${type}`;
            msg.style.display = 'block';
            setTimeout(() => {
                msg.style.display = 'none';
            }, 3000);
        }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """Serve the main UI."""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/words')
def api_words():
    """Get list of all words."""
    words = get_unique_words()
    return jsonify(words)


@app.route('/api/clusters/<word>')
def api_clusters(word):
    """Get clusters for a specific word."""
    clusters = get_clusters_for_word(word)
    return jsonify(clusters)


@app.route('/api/meanings/<word>')
def api_meanings(word):
    """Get saved meanings for a word."""
    corrections_dir = Path('data/06_metrics/cluster_corrections')
    correction_file = corrections_dir / f"{word}.json"

    if correction_file.exists():
        with open(correction_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return jsonify(data.get('meanings', {}))

    return jsonify({})


@app.route('/api/search')
def api_search():
    """Search for sentences containing the query."""
    query = request.args.get('query', '')
    language = request.args.get('language', 'both')
    max_results = int(request.args.get('max_results', 100))

    results = search_sentences(query, language, max_results)
    return jsonify(results)


@app.route('/api/save', methods=['POST'])
def api_save():
    """Save corrections to a JSON file."""
    data = request.json
    word = data['word']
    changes = data['changes']
    labels = data['labels']
    meanings = data.get('meanings', {})

    # Save to corrections directory
    corrections_dir = Path('data/06_metrics/cluster_corrections')
    corrections_dir.mkdir(parents=True, exist_ok=True)

    correction_file = corrections_dir / f"{word}.json"

    # Load existing corrections if any
    if correction_file.exists():
        with open(correction_file, 'r', encoding='utf-8') as f:
            existing = json.load(f)
    else:
        existing = {}

    # Merge with new corrections
    if 'changes' not in existing:
        existing['changes'] = {}
    if 'labels' not in existing:
        existing['labels'] = {}
    if 'meanings' not in existing:
        existing['meanings'] = {}

    existing['word'] = word
    existing['changes'].update(changes)
    existing['labels'].update(labels)
    existing['meanings'].update(meanings)
    existing['last_updated'] = pd.Timestamp.now().isoformat()

    # Save
    with open(correction_file, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    logger.info(f"Saved corrections for '{word}' to {correction_file}")

    return jsonify({
        'success': True,
        'message': f'Saved corrections for "{word}"'
    })


if __name__ == '__main__':
    # Load clusters on startup
    load_clusters()

    # Start server
    logger.info("Starting Cluster Review UI on http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
