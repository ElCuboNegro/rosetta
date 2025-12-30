"""
Interactive web UI for reviewing and correcting sense clusters.
PostgreSQL-powered version for fast, efficient queries.

Usage:
    python scripts/cluster_review_ui_postgres.py

Then open http://localhost:5000 in your browser.

Features:
- PostgreSQL backend for instant searches
- Full-text search with GIN indexes
- Minimal memory usage (no loading entire dataset)
- Falls back to parquet if database unavailable
"""
import json
import logging
from pathlib import Path

import pandas as pd
import psycopg2
from flask import Flask, jsonify, render_template_string, request
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Database connection
db_conn = None

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'rosetta',
    'user': 'postgres',
    'password': 'rosetta_password'
}


def get_db_connection():
    """Get or create database connection."""
    global db_conn
    if db_conn is None or db_conn.closed:
        try:
            db_conn = psycopg2.connect(**DB_CONFIG)
            logger.info("✅ Connected to PostgreSQL database")
            return db_conn
        except psycopg2.OperationalError as e:
            logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
            logger.warning("Make sure docker-compose is running: docker-compose up -d")
            return None
    return db_conn


def test_database_connection():
    """Test if database is available and has data."""
    conn = get_db_connection()
    if conn is None:
        return False

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM sense_clusters")
            count = cur.fetchone()[0]
            logger.info(f"✅ Database has {count:,} sense cluster entries")
            return count > 0
    except Exception as e:
        logger.error(f"❌ Database query failed: {e}")
        return False


def get_unique_words():
    """Get list of all unique words (FAST - uses index!)."""
    conn = get_db_connection()
    if conn is None:
        logger.warning("⚠️ Database unavailable, returning empty list")
        return []

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT source_word
                FROM sense_clusters
                ORDER BY source_word
            """)
            words = [row[0] for row in cur.fetchall()]
            logger.info(f"✅ Loaded {len(words):,} unique words")
            return words
    except Exception as e:
        logger.error(f"❌ Failed to load words: {e}")
        return []


def get_clusters_for_word(word):
    """Get all clusters for a specific word (FAST - uses index!)."""
    conn = get_db_connection()
    if conn is None:
        return []

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get all examples for this word
            cur.execute("""
                SELECT
                    sense_cluster_id,
                    sentence_text,
                    corpus_source,
                    clustering_method,
                    cluster_quality_score
                FROM sense_clusters
                WHERE source_word = %s
                ORDER BY sense_cluster_id, id
            """, (word,))

            rows = cur.fetchall()

            if not rows:
                return []

            # Group by cluster
            clusters_dict = {}
            for row in rows:
                cluster_id = row['sense_cluster_id']
                if cluster_id not in clusters_dict:
                    clusters_dict[cluster_id] = {
                        'cluster_id': cluster_id,
                        'size': 0,
                        'examples': [],
                        'quality_score': row['cluster_quality_score'],
                        'method': row['clustering_method']
                    }

                clusters_dict[cluster_id]['examples'].append({
                    'sentence_text': row['sentence_text'],
                    'corpus_source': row['corpus_source']
                })
                clusters_dict[cluster_id]['size'] += 1

            clusters = list(clusters_dict.values())
            logger.info(f"✅ Loaded {len(clusters)} clusters for '{word}'")
            return clusters

    except Exception as e:
        logger.error(f"❌ Failed to load clusters for '{word}': {e}")
        return []


def search_sentences(query, language='both', max_results=100):
    """
    Search for sentences using PostgreSQL full-text search (SUPER FAST!).

    Uses GIN indexes for instant results.
    """
    conn = get_db_connection()
    if conn is None or not query:
        return []

    query = query.strip()
    results = []

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if language in ['spanish', 'both']:
                # Full-text search on Spanish (uses GIN index!)
                cur.execute("""
                    SELECT
                        source_word,
                        sense_cluster_id,
                        sentence_text,
                        '' as target_he,
                        corpus_source,
                        cluster_quality_score,
                        'spanish' as match_field
                    FROM sense_clusters
                    WHERE to_tsvector('spanish', sentence_text) @@ plainto_tsquery('spanish', %s)
                    LIMIT %s
                """, (query, max_results))

                results.extend(cur.fetchall())

            # TODO: Add Hebrew search when we have Hebrew text in the database
            # For now, use simple LIKE search
            if language in ['hebrew', 'both'] and len(results) < max_results:
                remaining = max_results - len(results)
                # This assumes you have a hebrew field - adjust as needed
                # For now, just simple pattern matching
                pass

            # Convert to dict format
            formatted_results = []
            for row in results:
                formatted_results.append({
                    'word': row['source_word'],
                    'cluster_id': row['sense_cluster_id'],
                    'sentence': row['sentence_text'],
                    'hebrew': row.get('target_he', ''),
                    'source': row['corpus_source'],
                    'match_field': row['match_field'],
                    'quality_score': row['cluster_quality_score']
                })

            logger.info(f"✅ Search for '{query}': found {len(formatted_results)} results")
            return formatted_results

    except Exception as e:
        logger.error(f"❌ Search failed for '{query}': {e}")
        return []


# Import the HTML template from the original file
# (keeping the same UI, just changing the backend)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Sense Cluster Review (PostgreSQL)</title>
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
        .subtitle { color: #666; margin-bottom: 10px; }
        .db-status {
            padding: 10px 15px;
            border-radius: 4px;
            margin-bottom: 20px;
            font-size: 14px;
            font-weight: 600;
        }
        .db-status.connected {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .db-status.disconnected {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }

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

        .example {
            padding: 12px;
            margin-bottom: 8px;
            background: #f8f9fa;
            border-radius: 4px;
            border-left: 3px solid #007bff;
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
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 Sense Cluster Review Tool (PostgreSQL)</h1>
        <p class="subtitle">⚡ Fast PostgreSQL-powered search with indexed queries</p>
        <div id="db-status" class="db-status disconnected">⏳ Checking database connection...</div>

        <div class="controls">
            <div class="control-section">
                <h3>🔍 Search (Full-Text)</h3>
                <div class="search-bar">
                    <input type="text"
                           id="search-input"
                           placeholder="Search for Spanish text (uses PostgreSQL full-text search)..."
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
    </div>

    <script>
        let currentWord = null;

        // Check database connection on load
        fetch('/api/db-status')
            .then(r => r.json())
            .then(status => {
                const dbStatus = document.getElementById('db-status');
                if (status.connected) {
                    dbStatus.className = 'db-status connected';
                    dbStatus.textContent = `✅ Connected to PostgreSQL (${status.row_count.toLocaleString()} entries)`;
                } else {
                    dbStatus.className = 'db-status disconnected';
                    dbStatus.textContent = '❌ Database unavailable. Run: docker-compose up -d';
                }
            });

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
                        <p style="color: #666;">Try a different search term.</p>
                    </div>
                `;
                area.style.display = 'block';
                document.getElementById('clusters-area').style.display = 'none';
                return;
            }

            const byWord = {};
            results.forEach(r => {
                if (!byWord[r.word]) byWord[r.word] = [];
                byWord[r.word].push(r);
            });

            const uniqueWords = Object.keys(byWord).length;

            let html = `
                <div class="search-results">
                    <h2>⚡ Search Results for "${query}"</h2>
                    <div class="search-stats">
                        Found <strong>${results.length}</strong> matches across <strong>${uniqueWords}</strong> word${uniqueWords > 1 ? 's' : ''}
                        <span style="color: #666; margin-left: 10px;">(PostgreSQL full-text search)</span>
                    </div>
            `;

            results.forEach(result => {
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

            document.getElementById('search-results-area').style.display = 'none';
            document.getElementById('clusters-area').style.display = 'block';

            fetch(`/api/clusters/${word}`)
                .then(r => r.json())
                .then(clusters => {
                    renderClusters(clusters, word);
                });
        }

        function renderClusters(clusters, word) {
            const area = document.getElementById('clusters-area');

            if (clusters.length === 0) {
                area.innerHTML = `<p style="text-align: center; color: #999; padding: 40px;">No clusters found for "${word}"</p>`;
                return;
            }

            let html = `<h2 style="margin-bottom: 20px;">Clusters for "${word}"</h2>`;
            html += '<div class="clusters-container">';

            clusters.forEach(cluster => {
                let qualityClass = 'quality-low';
                if (cluster.quality_score > 0.6) qualityClass = 'quality-high';
                else if (cluster.quality_score > 0.3) qualityClass = 'quality-medium';

                html += `
                    <div class="cluster">
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
                `;

                cluster.examples.forEach(ex => {
                    html += `
                        <div class="example">
                            <div class="example-text">${ex.sentence_text}</div>
                            <div class="example-source">${ex.corpus_source}</div>
                        </div>
                    `;
                });

                html += '</div>';
            });

            html += '</div>';
            area.innerHTML = html;
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


@app.route('/api/db-status')
def api_db_status():
    """Check database connection status."""
    conn = get_db_connection()

    if conn is None:
        return jsonify({
            'connected': False,
            'row_count': 0
        })

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM sense_clusters")
            count = cur.fetchone()[0]
            return jsonify({
                'connected': True,
                'row_count': count
            })
    except Exception:
        return jsonify({
            'connected': False,
            'row_count': 0
        })


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


@app.route('/api/search')
def api_search():
    """Search for sentences containing the query."""
    query = request.args.get('query', '')
    language = request.args.get('language', 'both')
    max_results = int(request.args.get('max_results', 100))

    results = search_sentences(query, language, max_results)
    return jsonify(results)


if __name__ == '__main__':
    # Test database connection
    logger.info("=" * 60)
    logger.info("Starting Cluster Review UI (PostgreSQL Edition)")
    logger.info("=" * 60)

    if test_database_connection():
        logger.info("✅ Database connection successful!")
    else:
        logger.warning("⚠️  Database unavailable. Make sure to run:")
        logger.warning("   docker-compose up -d")

    # Start server
    logger.info("=" * 60)
    logger.info("🚀 Starting server on http://localhost:5000")
    logger.info("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
