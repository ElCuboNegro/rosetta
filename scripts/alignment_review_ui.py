"""
Interactive web UI for reviewing book alignment matches.

Usage:
    python scripts/alignment_review_ui.py

Then open http://localhost:5001 in your browser.
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
alignment_results = []
approved_pairs = []
rejected_pairs = []


def scan_book_pairs():
    """Scan for potential book pairs and their metadata."""
    # This will be populated from catalog or file scanning
    catalog_file = Path("data/02_intermediate/aligned_catalogs.parquet")

    pairs = []

    if catalog_file.exists():
        catalog = pd.read_parquet(catalog_file)
        logger.info(f"Loaded {len(catalog)} catalog entries")

        for _, row in catalog.iterrows():
            pairs.append({
                'spanish_file': row.get('spanish_file', 'unknown'),
                'hebrew_file': row.get('hebrew_file', 'unknown'),
                'spanish_title': row.get('match_title', row.get('spanish_title', 'Unknown')),
                'hebrew_title': row.get('he_title', row.get('hebrew_title', 'Unknown')),
                'match_score': row.get('title_similarity', 0.0),
                'spanish_sentences': row.get('spanish_sentences', 0),
                'hebrew_sentences': row.get('hebrew_sentences', 0),
                'ratio': 0.0,
                'status': 'pending'
            })
    else:
        # Scan file system
        logger.info("No catalog found, scanning file system...")
        es_dir = Path("data/01_raw/gutenberg_books/es")
        he_dir = Path("data/01_raw/ben_yehuda_dump/txt_stripped")

        if es_dir.exists():
            es_files = list(es_dir.glob("**/*.txt"))
            logger.info(f"Found {len(es_files)} Spanish books")

        if he_dir.exists():
            he_files = list(he_dir.glob("**/*.txt"))
            logger.info(f"Found {len(he_files)} Hebrew books")

    # Calculate ratios
    for pair in pairs:
        if pair['spanish_sentences'] > 0 and pair['hebrew_sentences'] > 0:
            pair['ratio'] = max(pair['spanish_sentences'], pair['hebrew_sentences']) / min(pair['spanish_sentences'], pair['hebrew_sentences'])
        else:
            pair['ratio'] = 0.0

    # Sort by ratio (worst first)
    pairs.sort(key=lambda x: x['ratio'], reverse=True)

    return pairs


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Book Alignment Review</title>
    <meta charset="UTF-8">
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }
        .container { max-width: 1600px; margin: 0 auto; }
        h1 { color: #333; margin-bottom: 10px; }
        .subtitle { color: #666; margin-bottom: 30px; }

        .stats {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: flex;
            gap: 30px;
        }
        .stat-item {
            flex: 1;
            text-align: center;
        }
        .stat-number {
            font-size: 36px;
            font-weight: bold;
            color: #007bff;
        }
        .stat-label {
            font-size: 14px;
            color: #666;
            margin-top: 5px;
        }

        .filters {
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: flex;
            gap: 15px;
            align-items: center;
        }
        .filters label {
            font-weight: 600;
            color: #333;
        }
        .filters select {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }

        .pair-list {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .pair-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: all 0.2s;
        }
        .pair-card:hover {
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }

        .pair-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 2px solid #eee;
        }

        .pair-titles {
            flex: 1;
        }
        .title-row {
            display: flex;
            align-items: center;
            margin-bottom: 8px;
        }
        .lang-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
            margin-right: 10px;
            min-width: 30px;
            text-align: center;
        }
        .lang-badge.es {
            background: #d4edda;
            color: #155724;
        }
        .lang-badge.he {
            background: #cce5ff;
            color: #004085;
        }
        .title-text {
            font-size: 16px;
            color: #333;
            font-weight: 500;
        }

        .pair-stats {
            text-align: right;
        }
        .ratio-badge {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 8px;
        }
        .ratio-badge.good {
            background: #d4edda;
            color: #155724;
        }
        .ratio-badge.warning {
            background: #fff3cd;
            color: #856404;
        }
        .ratio-badge.danger {
            background: #f8d7da;
            color: #721c24;
        }
        .match-score {
            font-size: 12px;
            color: #666;
        }

        .pair-details {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 15px;
        }
        .detail-box {
            padding: 12px;
            background: #f8f9fa;
            border-radius: 4px;
        }
        .detail-label {
            font-size: 11px;
            color: #666;
            text-transform: uppercase;
            font-weight: 600;
            margin-bottom: 5px;
        }
        .detail-value {
            font-size: 14px;
            color: #333;
        }

        .sentence-counts {
            display: flex;
            gap: 20px;
            align-items: center;
            margin-bottom: 15px;
        }
        .sentence-count {
            flex: 1;
            padding: 12px;
            background: #f8f9fa;
            border-radius: 4px;
            text-align: center;
        }
        .sentence-count-number {
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
        }
        .sentence-count-label {
            font-size: 11px;
            color: #666;
            text-transform: uppercase;
            margin-top: 5px;
        }

        .pair-actions {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
        }
        .btn {
            padding: 10px 24px;
            border: none;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-approve {
            background: #28a745;
            color: white;
        }
        .btn-approve:hover {
            background: #218838;
        }
        .btn-reject {
            background: #dc3545;
            color: white;
        }
        .btn-reject:hover {
            background: #c82333;
        }
        .btn-view {
            background: #17a2b8;
            color: white;
        }
        .btn-view:hover {
            background: #138496;
        }
        .btn-skip {
            background: #6c757d;
            color: white;
        }
        .btn-skip:hover {
            background: #5a6268;
        }

        .status-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .status-approved {
            background: #d4edda;
            color: #155724;
        }
        .status-rejected {
            background: #f8d7da;
            color: #721c24;
        }
        .status-pending {
            background: #fff3cd;
            color: #856404;
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

        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }
        .empty-state-icon {
            font-size: 64px;
            margin-bottom: 20px;
        }

        /* Sample preview modal */
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
        .modal-content {
            background: white;
            padding: 30px;
            border-radius: 8px;
            width: 90%;
            max-width: 900px;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #eee;
        }
        .modal-close {
            background: none;
            border: none;
            font-size: 28px;
            cursor: pointer;
            color: #999;
        }
        .sample-pair {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            padding: 15px;
            margin-bottom: 15px;
            background: #f8f9fa;
            border-radius: 4px;
        }
        .sample-text {
            font-size: 14px;
            line-height: 1.6;
            color: #333;
        }
        .sample-hebrew {
            direction: rtl;
            text-align: right;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 Book Alignment Review</h1>
        <p class="subtitle">Review and approve book pairs for alignment</p>

        <div class="stats">
            <div class="stat-item">
                <div class="stat-number" id="total-pairs">0</div>
                <div class="stat-label">Total Pairs</div>
            </div>
            <div class="stat-item">
                <div class="stat-number" id="pending-count" style="color: #ffc107;">0</div>
                <div class="stat-label">Pending Review</div>
            </div>
            <div class="stat-item">
                <div class="stat-number" id="approved-count" style="color: #28a745;">0</div>
                <div class="stat-label">Approved</div>
            </div>
            <div class="stat-item">
                <div class="stat-number" id="rejected-count" style="color: #dc3545;">0</div>
                <div class="stat-label">Rejected</div>
            </div>
        </div>

        <div class="filters">
            <label>Filter:</label>
            <select id="status-filter" onchange="filterPairs()">
                <option value="all">All Pairs</option>
                <option value="pending">Pending Only</option>
                <option value="approved">Approved Only</option>
                <option value="rejected">Rejected Only</option>
            </select>
            <label>Sort by:</label>
            <select id="sort-by" onchange="filterPairs()">
                <option value="ratio">Ratio (Worst First)</option>
                <option value="ratio-asc">Ratio (Best First)</option>
                <option value="title">Title (A-Z)</option>
            </select>
        </div>

        <div id="message" class="message"></div>

        <div id="pair-list" class="pair-list">
            <div class="empty-state">
                <div class="empty-state-icon">📖</div>
                <p>Loading book pairs...</p>
            </div>
        </div>
    </div>

    <!-- Sample Preview Modal -->
    <div id="preview-modal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>Sample Alignments</h2>
                <button class="modal-close" onclick="closePreview()">&times;</button>
            </div>
            <div id="preview-content">
                <p>Loading samples...</p>
            </div>
        </div>
    </div>

    <script>
        let allPairs = [];
        let currentFilter = 'all';
        let currentSort = 'ratio';

        // Load pairs on startup
        fetch('/api/pairs')
            .then(r => r.json())
            .then(pairs => {
                allPairs = pairs;
                renderPairs();
                updateStats();
            });

        function renderPairs() {
            const filtered = filterAndSort();
            const container = document.getElementById('pair-list');

            if (filtered.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">✅</div>
                        <p>No pairs match current filter</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = '';
            filtered.forEach((pair, idx) => {
                container.appendChild(createPairCard(pair, idx));
            });
        }

        function createPairCard(pair, idx) {
            const div = document.createElement('div');
            div.className = 'pair-card';
            div.dataset.index = idx;

            let ratioClass = 'good';
            if (pair.ratio > 3.0) ratioClass = 'danger';
            else if (pair.ratio > 2.0) ratioClass = 'warning';

            let statusBadge = '';
            if (pair.status !== 'pending') {
                statusBadge = `<span class="status-badge status-${pair.status}">${pair.status}</span>`;
            }

            div.innerHTML = `
                <div class="pair-header">
                    <div class="pair-titles">
                        <div class="title-row">
                            <span class="lang-badge es">ES</span>
                            <span class="title-text">${pair.spanish_title}</span>
                        </div>
                        <div class="title-row">
                            <span class="lang-badge he">HE</span>
                            <span class="title-text">${pair.hebrew_title}</span>
                        </div>
                    </div>
                    <div class="pair-stats">
                        <div class="ratio-badge ${ratioClass}">${pair.ratio.toFixed(1)}:1</div>
                        <div class="match-score">Title Match: ${(pair.match_score * 100).toFixed(0)}%</div>
                        ${statusBadge}
                    </div>
                </div>

                <div class="sentence-counts">
                    <div class="sentence-count">
                        <div class="sentence-count-number">${pair.spanish_sentences.toLocaleString()}</div>
                        <div class="sentence-count-label">Spanish Sentences</div>
                    </div>
                    <div class="sentence-count">
                        <div class="sentence-count-number">${pair.hebrew_sentences.toLocaleString()}</div>
                        <div class="sentence-count-label">Hebrew Sentences</div>
                    </div>
                </div>

                <div class="pair-details">
                    <div class="detail-box">
                        <div class="detail-label">Spanish File</div>
                        <div class="detail-value">${pair.spanish_file}</div>
                    </div>
                    <div class="detail-box">
                        <div class="detail-label">Hebrew File</div>
                        <div class="detail-value">${pair.hebrew_file}</div>
                    </div>
                </div>

                <div class="pair-actions">
                    ${pair.status === 'pending' ? `
                        <button class="btn btn-view" onclick="viewSamples(${idx})">View Samples</button>
                        <button class="btn btn-reject" onclick="rejectPair(${idx})">❌ Reject</button>
                        <button class="btn btn-approve" onclick="approvePair(${idx})">✅ Approve</button>
                    ` : `
                        <button class="btn btn-view" onclick="viewSamples(${idx})">View Samples</button>
                        <button class="btn btn-skip" onclick="resetPair(${idx})">Reset to Pending</button>
                    `}
                </div>
            `;

            return div;
        }

        function filterAndSort() {
            let filtered = allPairs;

            // Filter by status
            if (currentFilter !== 'all') {
                filtered = filtered.filter(p => p.status === currentFilter);
            }

            // Sort
            filtered = [...filtered].sort((a, b) => {
                if (currentSort === 'ratio') {
                    return b.ratio - a.ratio; // Worst first
                } else if (currentSort === 'ratio-asc') {
                    return a.ratio - b.ratio; // Best first
                } else if (currentSort === 'title') {
                    return a.spanish_title.localeCompare(b.spanish_title);
                }
                return 0;
            });

            return filtered;
        }

        function filterPairs() {
            currentFilter = document.getElementById('status-filter').value;
            currentSort = document.getElementById('sort-by').value;
            renderPairs();
        }

        function approvePair(idx) {
            const filtered = filterAndSort();
            const pair = filtered[idx];
            pair.status = 'approved';

            fetch('/api/approve', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    spanish_file: pair.spanish_file,
                    hebrew_file: pair.hebrew_file
                })
            })
            .then(r => r.json())
            .then(result => {
                showMessage('Pair approved', 'success');
                renderPairs();
                updateStats();
            });
        }

        function rejectPair(idx) {
            const filtered = filterAndSort();
            const pair = filtered[idx];
            pair.status = 'rejected';

            fetch('/api/reject', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    spanish_file: pair.spanish_file,
                    hebrew_file: pair.hebrew_file
                })
            })
            .then(r => r.json())
            .then(result => {
                showMessage('Pair rejected', 'success');
                renderPairs();
                updateStats();
            });
        }

        function resetPair(idx) {
            const filtered = filterAndSort();
            const pair = filtered[idx];
            pair.status = 'pending';
            renderPairs();
            updateStats();
        }

        function viewSamples(idx) {
            const filtered = filterAndSort();
            const pair = filtered[idx];

            // Request sample alignments from backend
            fetch(`/api/samples?spanish_file=${encodeURIComponent(pair.spanish_file)}&hebrew_file=${encodeURIComponent(pair.hebrew_file)}`)
                .then(r => r.json())
                .then(samples => {
                    displaySamples(samples);
                });
        }

        function displaySamples(samples) {
            const content = document.getElementById('preview-content');

            if (samples.length === 0) {
                content.innerHTML = '<p>No sample alignments available yet. Approve this pair to generate alignments.</p>';
            } else {
                let html = '<p>Top 10 aligned sentence pairs (by similarity):</p>';
                samples.forEach((sample, i) => {
                    html += `
                        <div class="sample-pair">
                            <div class="sample-text">${sample.spanish}</div>
                            <div class="sample-text sample-hebrew">${sample.hebrew}</div>
                        </div>
                    `;
                });
                content.innerHTML = html;
            }

            document.getElementById('preview-modal').classList.add('active');
        }

        function closePreview() {
            document.getElementById('preview-modal').classList.remove('active');
        }

        function updateStats() {
            document.getElementById('total-pairs').textContent = allPairs.length;
            document.getElementById('pending-count').textContent = allPairs.filter(p => p.status === 'pending').length;
            document.getElementById('approved-count').textContent = allPairs.filter(p => p.status === 'approved').length;
            document.getElementById('rejected-count').textContent = allPairs.filter(p => p.status === 'rejected').length;
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

        // Close modal when clicking outside
        document.getElementById('preview-modal').addEventListener('click', function(e) {
            if (e.target === this) {
                closePreview();
            }
        });
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """Serve the main UI."""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/pairs')
def api_pairs():
    """Get all book pairs."""
    global alignment_results
    if not alignment_results:
        alignment_results = scan_book_pairs()
    return jsonify(alignment_results)


@app.route('/api/approve', methods=['POST'])
def api_approve():
    """Approve a book pair."""
    data = request.json
    spanish_file = data['spanish_file']
    hebrew_file = data['hebrew_file']

    # Save to approved pairs
    approved_file = Path('data/06_metrics/approved_book_pairs.json')
    approved_file.parent.mkdir(parents=True, exist_ok=True)

    if approved_file.exists():
        with open(approved_file, 'r', encoding='utf-8') as f:
            approved = json.load(f)
    else:
        approved = []

    approved.append({
        'spanish_file': spanish_file,
        'hebrew_file': hebrew_file,
        'approved_at': pd.Timestamp.now().isoformat()
    })

    with open(approved_file, 'w', encoding='utf-8') as f:
        json.dump(approved, f, ensure_ascii=False, indent=2)

    logger.info(f"Approved pair: {spanish_file} <-> {hebrew_file}")

    return jsonify({'success': True, 'message': 'Pair approved'})


@app.route('/api/reject', methods=['POST'])
def api_reject():
    """Reject a book pair."""
    data = request.json
    spanish_file = data['spanish_file']
    hebrew_file = data['hebrew_file']

    # Save to rejected pairs
    rejected_file = Path('data/06_metrics/rejected_book_pairs.json')
    rejected_file.parent.mkdir(parents=True, exist_ok=True)

    if rejected_file.exists():
        with open(rejected_file, 'r', encoding='utf-8') as f:
            rejected = json.load(f)
    else:
        rejected = []

    rejected.append({
        'spanish_file': spanish_file,
        'hebrew_file': hebrew_file,
        'rejected_at': pd.Timestamp.now().isoformat()
    })

    with open(rejected_file, 'w', encoding='utf-8') as f:
        json.dump(rejected, f, ensure_ascii=False, indent=2)

    logger.info(f"Rejected pair: {spanish_file} <-> {hebrew_file}")

    return jsonify({'success': True, 'message': 'Pair rejected'})


@app.route('/api/samples')
def api_samples():
    """Get sample alignments for a book pair."""
    spanish_file = request.args.get('spanish_file')
    hebrew_file = request.args.get('hebrew_file')

    # Try to load from aligned books data
    aligned_file = Path('data/02_intermediate/aligned_books.parquet')

    samples = []

    if aligned_file.exists():
        aligned_df = pd.read_parquet(aligned_file)

        # Filter by book pair
        pair_data = aligned_df[
            (aligned_df['source_book'] == spanish_file) &
            (aligned_df['target_book'] == hebrew_file)
        ]

        if not pair_data.empty:
            # Get top 10 by similarity
            top_samples = pair_data.nlargest(10, 'similarity')

            samples = [
                {
                    'spanish': row['source_es'],
                    'hebrew': row['target_he'],
                    'similarity': row['similarity']
                }
                for _, row in top_samples.iterrows()
            ]

    return jsonify(samples)


if __name__ == '__main__':
    logger.info("Starting Book Alignment Review UI on http://localhost:5001")
    app.run(debug=True, host='0.0.0.0', port=5001)
